"""Supervise the Django development server and the Priceva worker together."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


def stop_child(child):
    if child.poll() is not None:
        # The autoreloader can outlive its group leader after an abnormal exit.
        try:
            if os.name == "nt":
                os.kill(child.pid, signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(child.pid, signal.SIGINT)
        except OSError:
            pass
        return
    try:
        if os.name == "nt":
            child.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(child.pid, signal.SIGINT)
        child.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        child.wait()


class Command(BaseCommand):
    help = "Start the website and Priceva scheduling with one command."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("addrport", nargs="?", default="127.0.0.1:8000")
        parser.add_argument("--noreload", action="store_true")
        parser.add_argument(
            "--prepare-pricem",
            action="store_true",
            help="Apply the one-time Priceva SQL schema preparation",
        )
        parser.add_argument(
            "--poll-seconds", type=float, default=settings.PRICEM_POLL_SECONDS
        )

    def handle(self, *args, **options):
        if options["poll_seconds"] <= 0:
            raise CommandError("--poll-seconds must be positive")
        if options["prepare_pricem"]:
            call_command("pricem_prepare", stdout=self.stdout, stderr=self.stderr)
        manage = Path(settings.BASE_DIR) / "manage.py"
        common = [sys.executable, "-u", str(manage)]
        commands = [
            common + ["pricem_worker", "--poll-seconds", str(options["poll_seconds"])],
            common + ["runserver", options["addrport"]],
        ]
        if options["noreload"]:
            commands[1].append("--noreload")
        if options.get("settings"):
            for command in commands:
                command.extend(["--settings", options["settings"]])
        process_options = {"cwd": str(settings.BASE_DIR)}
        if os.name == "nt":
            process_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            process_options["start_new_session"] = True
        children = []
        previous = {}

        def stop(signum, frame):
            raise KeyboardInterrupt

        for name in ("SIGTERM", "SIGBREAK"):
            signum = getattr(signal, name, None)
            if signum is not None:
                previous[signum] = signal.signal(signum, stop)
        self.stdout.write("Starting website + Priceva worker. Ctrl+C stops both.")
        self.stdout.flush()
        try:
            for command in commands:
                children.append(subprocess.Popen(command, **process_options))
            while True:
                for label, child in zip(("Priceva worker", "Django server"), children):
                    code = child.poll()
                    if code is not None:
                        raise CommandError(
                            f"{label} exited with code {code}; both processes stopped"
                        )
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stdout.write("Stopping website and Priceva worker...")
        finally:
            for child in children:
                stop_child(child)
            for signum, handler in previous.items():
                signal.signal(signum, handler)
