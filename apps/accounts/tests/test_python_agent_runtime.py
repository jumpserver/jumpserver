import json
import tempfile
import threading
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from accounts.clients.python.jms_pam._agent import runtime, storage
from accounts.clients.python.jms_pam.agent import Agent
from accounts.clients.python.jms_pam.exceptions import PAMError
from accounts.clients.python.jms_pam.models import AgentSync


class PythonAgentRuntimeTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        configuration = {
            "credential_keys": ["db"],
            "confirmation_keys": ["db"],
            "delivery_mode": "socket",
            "delivery_root": str(self.root / "output"),
            "socket_path": str(self.root / "agent.sock"),
            "app_user": "app",
        }
        self.config_file = self.root / "agent.json"
        self.config_file.write_text(
            json.dumps(
                {
                    "endpoint": "https://testserver",
                    "app_id": "app",
                    "app_secret": "secret",
                    "org_id": "org",
                    "instance_id": "worker",
                    "configuration_id": "config",
                    "configuration": configuration,
                    "capabilities": dict(configuration),
                    "state_file": str(self.root / "state.json"),
                    "credential_file": str(self.root / "credentials.json"),
                    "delivery_file": str(self.root / "delivered.json"),
                }
            )
        )
        self.remote = Mock()
        self.remote.list_application_commands.return_value = []
        with patch.object(runtime, "Client", return_value=self.remote):
            self.agent = Agent(str(self.config_file))
        self.agent.credentials = {
            "db": {
                "key": "db",
                "revision": 2,
                "account_id": "account",
                "secret": "cached",
            }
        }
        self.agent.delivered = {"db": {"key": "db", "revision": 2}}
        self.remote.sync_agent.return_value = AgentSync.from_dict(
            {
                "config_digest": "digest",
                "credentials": [
                    {"key": "db", "revision": 2, "available": True, "changed": False}
                ],
                "removed_keys": [],
                "date_last_synced": "now",
            }
        )

    def test_event_worker_continues_after_failure_and_preserves_order(self):
        self.agent.start_local_server = Mock(return_value=Mock())
        calls = []

        def sync(refresh_keys=()):
            calls.append((list(refresh_keys), threading.get_ident()))
            if len(calls) == 2:
                raise OSError("temporary failure")

        self.agent.safe_sync = Mock(side_effect=sync)
        self.remote.watch_credential_events.return_value = iter(
            [
                {"event": "credential.updated", "credential_key": "first"},
                {"event": "credential.updated", "credential_key": "second"},
            ]
        )
        with self.assertLogs(level="WARNING"):
            self.agent.run()
        self.assertEqual([keys for keys, _ in calls], [[], ["first"], ["second"]])
        self.assertEqual({thread for _, thread in calls}, {threading.get_ident()})
        self.remote.close.assert_called_once()
        self.agent.start_local_server.return_value.shutdown.assert_called_once()
        self.assertFalse(any(t.name == "jms-pam-events" for t in threading.enumerate()))

    def test_periodic_reconciliation_runs_without_events(self):
        self.agent.config["reconcile_interval"] = 0.01
        self.agent.start_local_server = Mock(return_value=Mock())
        stop = threading.Event()

        def events(event):
            event.wait(1)
            yield from ()

        def sync(**_):
            if self.agent.safe_sync.call_count == 2:
                stop.set()

        self.remote.watch_credential_events.side_effect = events
        self.agent.safe_sync = Mock(side_effect=sync)
        self.agent.run(stop)
        self.assertEqual(self.agent.safe_sync.call_count, 2)

    def test_busy_reconciliation_does_not_discard_notification(self):
        attempted = threading.Event()

        def reconcile():
            attempted.set()
            self.agent.safe_sync(refresh_keys=["db"])

        with patch.object(self.agent, "_sync", return_value=None) as sync:
            with self.agent.sync_lock:
                worker = threading.Thread(target=reconcile)
                worker.start()
                self.assertTrue(attempted.wait(1))
                sync.assert_not_called()
            worker.join(timeout=1)
            self.assertFalse(worker.is_alive())
        sync.assert_called_once_with(["db"])

    def test_identity_failure_disables_local_access_and_preserves_cache(self):
        self.remote.sync_agent.side_effect = PAMError(
            "client_disabled", "DO_NOT_LOG_SECRET", status_code=403
        )
        with self.assertRaises(PAMError):
            self.agent.sync()
        self.assertTrue(self.agent.access_denied)
        self.assertEqual(self.agent.credentials["db"]["secret"], "cached")
        with self.assertRaises(PermissionError):
            self.agent.local_credential("db")
        persisted = storage.read_json(self.config_file)
        self.assertEqual(persisted["sync_error"], "PAMError")
        self.assertNotIn("DO_NOT_LOG_SECRET", self.config_file.read_text())

    def test_confirmation_requires_account_and_revision_match(self):
        self.agent.state = {
            "db": {"key": "db", "revision": 2, "account_id": "old-account"}
        }
        self.agent.report_confirmations()
        self.remote.confirm_credential.assert_not_called()
        self.agent.finish_switch_command(
            {
                "command_id": "command",
                "credential_key": "db",
                "revision": 2,
                "account_id": "old-account",
            }
        )
        self.remote.report_application_command_result.assert_not_called()

    def test_failed_authorization_snapshot_disables_local_access(self):
        self.remote.sync_agent.side_effect = PAMError(
            "credential_not_authorized", "Denied", status_code=403
        )
        with self.assertRaises(PAMError):
            self.agent.sync()
        with self.assertRaises(PermissionError):
            self.agent.local_credential("db")

    def test_network_failure_keeps_previously_authorized_cache_available(self):
        self.remote.sync_agent.side_effect = PAMError("NetworkError", "offline")
        with self.assertRaises(PAMError):
            self.agent.sync()
        self.assertEqual(self.agent.local_credential("db")["secret"], "cached")

    def test_successful_signed_sync_restores_disabled_access(self):
        self.agent.set_access_denied(True, "client_disabled")
        self.agent.sync()
        self.assertFalse(self.agent.access_denied)
        self.assertEqual(self.agent.local_credential("db")["secret"], "cached")

    def test_delivery_records_the_snapshot_that_was_written(self):
        def write(items, _):
            self.assertEqual(items["db"]["revision"], 2)
            self.agent.credentials["db"] = {"key": "db", "revision": 3}

        with patch.object(runtime, "deliver_credentials", side_effect=write):
            self.agent.deliver({"db"})
        self.assertEqual(self.agent.delivered["db"]["revision"], 2)

    def test_delivery_refuses_revoked_cached_credentials(self):
        self.agent.authorized_keys.clear()
        with patch.object(runtime, "deliver_credentials") as deliver:
            with self.assertRaises(PermissionError):
                self.agent.deliver({"db"})
        deliver.assert_not_called()

    def test_one_failed_command_does_not_block_other_commands(self):
        commands = [{"command_id": "first"}, {"command_id": "second"}]
        self.remote.list_application_commands.return_value = commands
        with patch.object(
            self.agent, "handle_command", side_effect=[ValueError(), None]
        ) as handle:
            with self.assertLogs(level="WARNING"):
                self.agent.process_commands()
        self.assertEqual([call.args[0] for call in handle.call_args_list], commands)

    def test_socket_start_failure_releases_remote_client(self):
        with patch.object(
            self.agent, "start_local_server", side_effect=OSError("unavailable")
        ):
            with self.assertRaises(OSError):
                self.agent.run()
        self.remote.close.assert_called_once()

    def test_atomic_write_failure_removes_temporary_secret_file(self):
        target = self.root / "output.json"
        target.write_text("old")
        with patch.object(storage.os, "fsync", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                storage.atomic_write(target, "new-secret")
        self.assertEqual(target.read_text(), "old")
        self.assertEqual(list(self.root.glob(".output.json.*")), [])
