import signal
import threading

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from datapull_service.pricem.errors import ImportConfigurationError, safe_error
from datapull_service.pricem.runner import run_tick
from datapull_service.pricem.schema import verify_schema


class Command(BaseCommand):
    help = "Keep importing Priceva according to the database schedule until Ctrl+C."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--poll-seconds", type=float, default=settings.PRICEM_POLL_SECONDS
        )

    def handle(self, *args, **options):
        if options["poll_seconds"] <= 0:
            raise CommandError("--poll-seconds must be positive")
        stopped = threading.Event()
        previous_handlers = {}

        def stop(signum, frame):
            raise KeyboardInterrupt

        for name in ("SIGTERM", "SIGBREAK"):
            signum = getattr(signal, name, None)
            if signum is not None:
                previous_handlers[signum] = signal.signal(signum, stop)
        previous_message = None
        checked = False
        self.stdout.write("[Priceva] Worker started; Ctrl+C stops it")
        try:
            while not stopped.is_set():
                close_old_connections()
                try:
                    if not checked:
                        verify_schema()
                        checked = True
                    result = run_tick()
                    message = f"[Priceva] {result.status}: {result.message}"
                    if result.run_id is not None:
                        message += f"; run={result.run_id}"
                except ImportConfigurationError as error:
                    raise CommandError(safe_error(error)) from None
                except Exception as error:
                    message = f"[Priceva] error: {safe_error(error)}"
                finally:
                    close_old_connections()
                if message != previous_message:
                    self.stdout.write(message)
                    self.stdout.flush()
                    previous_message = message
                stopped.wait(options["poll_seconds"])
        except KeyboardInterrupt:
            self.stdout.write("[Priceva] Worker stopped; uncommitted data rolled back")
        finally:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
