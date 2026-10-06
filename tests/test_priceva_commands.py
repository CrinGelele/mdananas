from io import StringIO
import os
import signal
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from tests.support import DatabaseTest
from django.core.management import call_command
from django.core.management.base import CommandError
from datapull_service.management.commands.runsite import stop_child
from datapull_service.pricem.errors import ImportLockLost
from datapull_service.pricem.runner import TickResult


class CommandTests(DatabaseTest):
    @unittest.skipIf(os.name == "nt", "POSIX process-group integration test")
    def test_stops_a_real_child_process(self):
        child = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-c",
                'import time\nprint("ready", flush=True)\ntry:\n while True: time.sleep(1)\nexcept KeyboardInterrupt: pass',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            text=True,
        )
        try:
            self.assertEqual(child.stdout.readline().strip(), "ready")
            stop_child(child)
            self.assertEqual(child.poll(), 0)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
            child.stdout.close()
            child.stderr.close()

    def test_stops_autoreloader_group_even_if_parent_already_exited(self):
        child = Mock(pid=4321)
        child.poll.return_value = 1
        with (
            patch("datapull_service.management.commands.runsite.os.name", "posix"),
            patch("datapull_service.management.commands.runsite.os.killpg") as kill,
        ):
            stop_child(child)
        kill.assert_called_once_with(4321, signal.SIGINT)

    def test_pricem_run_preserves_error_exit_code(self):
        with (
            patch("datapull_service.management.commands.pricem_run.verify_schema"),
            patch(
                "datapull_service.management.commands.pricem_run.run_tick",
                return_value=TickResult("failed", "bad payload", 10),
            ),
        ):
            with self.assertRaises(CommandError):
                call_command("pricem_run", stdout=StringIO())

    def test_worker_recovers_after_lost_sql_lock(self):
        output = StringIO()
        with (
            patch("datapull_service.management.commands.pricem_worker.verify_schema"),
            patch(
                "datapull_service.management.commands.pricem_worker.run_tick",
                side_effect=[
                    ImportLockLost("lost session"),
                    TickResult("idle", "alive"),
                    KeyboardInterrupt,
                ],
            ),
            patch(
                "datapull_service.management.commands.pricem_worker.threading.Event"
            ) as event,
        ):
            event.return_value.is_set.return_value = False
            call_command("pricem_worker", stdout=output)
        self.assertIn("lost session", output.getvalue())
        self.assertIn("alive", output.getvalue())

    def test_runsite_uses_current_python_and_stops_both_if_child_exits(self):
        worker, server = Mock(), Mock()
        worker.poll.return_value = 1
        server.poll.return_value = None
        with (
            patch(
                "datapull_service.management.commands.runsite.subprocess.Popen",
                side_effect=[worker, server],
            ) as popen,
            patch("datapull_service.management.commands.runsite.stop_child") as stop,
        ):
            with self.assertRaisesRegex(CommandError, "Priceva worker exited"):
                call_command(
                    "runsite", "127.0.0.1:9000", "--noreload", stdout=StringIO()
                )
        commands = [call.args[0] for call in popen.call_args_list]
        self.assertEqual(commands[0][0], sys.executable)
        self.assertIn("pricem_worker", commands[0])
        self.assertIn("runserver", commands[1])
        self.assertIn("--noreload", commands[1])
        self.assertIn("127.0.0.1:9000", commands[1])
        self.assertEqual(stop.call_count, 2)

    def test_runsite_ctrl_c_stops_both_children(self):
        children = [Mock(), Mock()]
        for child in children:
            child.poll.return_value = None
        with (
            patch(
                "datapull_service.management.commands.runsite.subprocess.Popen",
                side_effect=children,
            ),
            patch(
                "datapull_service.management.commands.runsite.time.sleep",
                side_effect=KeyboardInterrupt,
            ),
            patch("datapull_service.management.commands.runsite.stop_child") as stop,
        ):
            call_command("runsite", stdout=StringIO())
        self.assertEqual([call.args[0] for call in stop.call_args_list], children)

    def test_runsite_partial_start_failure_cleans_up_worker(self):
        worker = Mock()
        with (
            patch(
                "datapull_service.management.commands.runsite.subprocess.Popen",
                side_effect=[worker, OSError("cannot start server")],
            ),
            patch("datapull_service.management.commands.runsite.stop_child") as stop,
        ):
            with self.assertRaises(OSError):
                call_command("runsite", stdout=StringIO())
        stop.assert_called_once_with(worker)

    def test_windows_shutdown_sends_break_to_process_group(self):
        child = Mock()
        child.poll.return_value = None
        with (
            patch("datapull_service.management.commands.runsite.os.name", "nt"),
            patch.object(signal, "CTRL_BREAK_EVENT", 1, create=True),
        ):
            stop_child(child)
        child.send_signal.assert_called_once_with(1)
        child.wait.assert_called_once_with(timeout=10)

    def test_windows_shutdown_kills_tree_after_timeout(self):
        child = Mock(pid=1234)
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired("child", 10), 0]
        with (
            patch("datapull_service.management.commands.runsite.os.name", "nt"),
            patch.object(signal, "CTRL_BREAK_EVENT", 1, create=True),
            patch(
                "datapull_service.management.commands.runsite.subprocess.run"
            ) as kill,
        ):
            stop_child(child)
        self.assertEqual(
            kill.call_args.args[0], ["taskkill", "/PID", "1234", "/T", "/F"]
        )

    def test_sql_lock_does_not_run_on_wrong_backend(self):
        from datapull_service.pricem.locking import import_lock

        with self.assertRaisesRegex(Exception, "requires SQL Server"):
            with import_lock():
                self.fail("unexpected lock")
