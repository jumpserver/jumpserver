import ast
from pathlib import Path
from threading import Event, Thread, current_thread
from unittest import TestCase
from unittest.mock import Mock, patch

import websocket
from accounts.clients.python.jms_pam import Client
from accounts.clients.python.jms_pam._event_dispatcher import EventDispatcher
from accounts.clients.python.jms_pam.models import Credential


class PythonEventHookTests(TestCase):
    def setUp(self):
        self.client = Client(
            "https://testserver",
            app_id="application",
            app_secret="secret",
            instance_id="orders-worker-1",
        )
        self.addCleanup(self.client.close)
        self.credential = Credential.from_dict(
            {
                "key": "database",
                "revision": 2,
                "asset": {
                    "id": "asset",
                    "name": "db",
                    "address": "127.0.0.1",
                    "platform": {
                        "id": "platform",
                        "name": "PostgreSQL",
                        "category": "database",
                        "type": "postgresql",
                    },
                },
                "account": {
                    "id": "account",
                    "name": "db-user",
                    "username": "app",
                    "secret_type": "password",
                    "secret": "database-secret",
                },
            }
        )
        self.subscription = {
            "event": "credential.updated",
            "account_id": "account",
            "credential_key": "database:account",
            "credential_mode": "subscription",
        }
        self.client.get_credential = Mock(return_value=self.credential)
        self.client.confirm_credential = Mock()
        self.client.on_credential_changed = Mock()
        self.client.on_credential_revoked = Mock()
        self.client.on_event = Mock()
        self.client.on_event_error = Mock()

    def watch(self, events):
        with patch.object(
            self.client, "watch_credential_events", return_value=iter(events)
        ):
            self.client.watch_events()

    def test_initial_and_reconnect_snapshots_and_updates_fetch_by_mode(self):
        rotation = {
            "key": "rotation-key",
            "credential_mode": "alternating_rotation",
        }
        snapshot = {"event": "snapshot", "credentials": [self.subscription, rotation]}
        events = [snapshot, self.subscription, snapshot]
        self.watch(events)
        self.assertEqual(
            [call.kwargs for call in self.client.get_credential.call_args_list],
            [
                {"key": "database:account", "allow_local_fallback": False},
                {"key": "rotation-key", "allow_local_fallback": False},
                {"key": "database:account", "allow_local_fallback": False},
                {"key": "database:account", "allow_local_fallback": False},
                {"key": "rotation-key", "allow_local_fallback": False},
            ],
        )
        self.assertEqual(self.client.on_credential_changed.call_count, 5)
        self.client.on_event.assert_any_call(snapshot)
        self.client.on_event_error.assert_not_called()
        self.client.confirm_credential.assert_not_called()

    def test_lifecycle_commands_and_policy_subscription_events_do_not_fetch(self):
        revoked = {"event": "credential.revoked", "credential_key": "database"}
        self.watch(
            [
                {"event": "credential.rotation.completed"},
                {"event": "configuration.updated"},
                {**self.subscription, "account_id": None},
                {**self.subscription, "command_id": "command"},
                revoked,
            ]
        )
        self.client.get_credential.assert_not_called()
        self.client.on_credential_revoked.assert_called_once_with(revoked)

    def test_outdated_api_revision_is_retried_without_application(self):
        dispatcher = EventDispatcher(self.client)
        dispatcher._dispatch({**self.subscription, "revision": 3})
        self.client.on_credential_changed.assert_not_called()
        self.client.on_event_error.assert_called_once()
        self.assertTrue(dispatcher.pending)

    def test_older_event_does_not_cancel_pending_newer_revision(self):
        dispatcher = EventDispatcher(self.client)
        dispatcher._dispatch({**self.subscription, "revision": 3})
        dispatcher._dispatch({**self.subscription, "revision": 2})
        self.client.on_credential_changed.assert_not_called()
        self.client.get_credential.assert_called_once()
        self.assertEqual(
            dispatcher.pending[("key", "database:account")].update["revision"], 3
        )

    def test_bad_snapshot_item_does_not_prevent_later_credentials(self):
        self.watch([{"event": "snapshot", "credentials": [None, self.subscription]}])
        self.client.on_event_error.assert_called_once()
        self.client.on_credential_changed.assert_called_once_with(self.credential)

    def test_callback_failure_does_not_stop_later_events_and_is_retried(self):
        dispatcher = EventDispatcher(self.client)
        self.client.on_credential_changed.side_effect = [RuntimeError("failed"), None]
        dispatcher._dispatch(self.subscription)
        failed = self.client.on_event_error.call_args.args[0]
        self.assertIsInstance(failed, RuntimeError)
        dispatcher.pending[("key", "database:account")].due = 0
        dispatcher._retry()
        self.assertEqual(self.client.get_credential.call_count, 2)
        self.assertEqual(self.client.on_credential_changed.call_count, 2)
        self.assertFalse(dispatcher.pending)
        self.client.confirm_credential.assert_not_called()

    def test_fetch_failure_and_failed_error_hook_keep_processing(self):
        self.client.get_credential.side_effect = [
            RuntimeError("DO_NOT_LOG_SECRET"),
            self.credential,
        ]
        self.client.on_event_error.side_effect = RuntimeError("ANOTHER_SECRET")
        with self.assertLogs(
            "accounts.clients.python.jms_pam.client", level="WARNING"
        ) as logs:
            self.watch([self.subscription, self.subscription])
        self.assertNotIn("DO_NOT_LOG_SECRET", str(logs.output))
        self.assertNotIn("ANOTHER_SECRET", str(logs.output))
        self.client.on_credential_changed.assert_called_once_with(self.credential)

    def test_background_retries_without_another_event(self):
        applied = Event()

        def stream(stop_event):
            yield self.subscription
            stop_event.wait(3)

        def apply(credential):
            if self.client.on_credential_changed.call_count == 1:
                raise RuntimeError("temporary failure")
            applied.set()

        self.client.on_credential_changed.side_effect = apply
        with patch.object(self.client, "watch_credential_events", side_effect=stream):
            self.client.start_events()
            try:
                self.assertTrue(applied.wait(3))
            finally:
                self.client.stop_events()
        self.assertEqual(self.client.get_credential.call_count, 2)
        self.client.on_event_error.assert_called_once()

    def test_snapshot_revocation_and_configuration_cancel_pending_retries(self):
        dispatcher = EventDispatcher(self.client)
        self.client.get_credential.side_effect = RuntimeError("failed")
        for event in (
            {"event": "snapshot", "credentials": []},
            {"event": "credential.revoked"},
            {"event": "configuration.updated"},
        ):
            dispatcher._dispatch(self.subscription)
            self.assertTrue(dispatcher.pending)
            dispatcher._dispatch(event)
            self.assertFalse(dispatcher.pending)

    def test_idle_receiver_keeps_waiting_and_stop_does_not_close_http(self):
        entered = Event()
        connection = Mock()

        def recv():
            entered.set()
            raise websocket.WebSocketTimeoutException()

        connection.recv.side_effect = recv
        with patch(
            "accounts.clients.python.jms_pam._events.websocket.create_connection",
            return_value=connection,
        ):
            self.client.start_events()
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    self.client.watch_events()
                self.client.stop_events()
            finally:
                self.client.stop_events()
        self.assertTrue(self.client._event_dispatcher.finished.is_set())
        self.assertFalse(self.client._closed)
        self.client.on_event.assert_not_called()
        connection.close.assert_called_once()

    def test_blocking_watch_returns_after_external_stop(self):
        entered, stop = Event(), Event()

        def stream(stop_event):
            entered.set()
            stop_event.wait(2)
            yield from ()

        with patch.object(self.client, "watch_credential_events", side_effect=stream):
            caller = Thread(target=self.client.watch_events, args=(stop,))
            caller.start()
            try:
                self.assertTrue(entered.wait(2))
                self.assertTrue(caller.is_alive())
                stop.set()
            finally:
                stop.set()
                caller.join(2)
            self.assertFalse(caller.is_alive())

    def test_slow_hook_does_not_stop_reader_and_close_waits_for_hook(self):
        entered, received_next, release, closed = Event(), Event(), Event(), Event()
        threads = []

        def stream(stop_event):
            threads.append(current_thread())
            yield self.subscription
            entered.wait(2)
            received_next.set()
            stop_event.wait(2)

        def apply(credential):
            threads.append(current_thread())
            entered.set()
            release.wait(2)

        self.client.on_credential_changed.side_effect = apply
        with patch.object(self.client, "watch_credential_events", side_effect=stream):
            self.client.start_events()
            closer = Thread(target=lambda: (self.client.close(), closed.set()))
            try:
                self.assertTrue(entered.wait(2))
                self.assertTrue(received_next.wait(2))
                closer.start()
                self.assertFalse(closed.wait(0.05))
                release.set()
                self.assertTrue(closed.wait(2))
            finally:
                release.set()
                self.client.close()
                if closer.ident is not None:
                    closer.join(2)
        self.assertIsNot(threads[0], threads[1])
        self.assertFalse(self.client._event_dispatcher.reader.is_alive())
        self.assertFalse(self.client._event_dispatcher.worker.is_alive())

    def test_stop_unblocks_a_reader_waiting_on_a_full_queue(self):
        entered, full, release = Event(), Event(), Event()

        def stream(stop_event):
            yield self.subscription
            entered.wait(2)
            for index in range(129):
                if index == 128:
                    full.set()
                yield self.subscription

        def apply(credential):
            entered.set()
            release.wait(2)

        self.client.on_credential_changed.side_effect = apply
        with patch.object(self.client, "watch_credential_events", side_effect=stream):
            self.client.start_events()
            try:
                self.assertTrue(full.wait(2))
                self.assertTrue(self.client._event_dispatcher.events.full())
                self.client._event_dispatcher.request_stop()
            finally:
                release.set()
                self.client.stop_events()
        self.assertFalse(self.client._event_dispatcher.reader.is_alive())
        self.client.on_credential_changed.assert_called_once()

    def test_hook_can_close_its_own_client(self):
        self.client.on_credential_changed.side_effect = lambda credential: (
            self.client.close()
        )
        self.watch([self.subscription, self.subscription])
        self.client.on_credential_changed.assert_called_once()
        self.assertTrue(self.client._closed)

    def test_listener_can_restart_after_stop_but_not_after_close(self):
        for _ in range(2):
            self.watch([self.subscription])
        self.assertEqual(self.client.on_credential_changed.call_count, 2)
        self.client.close()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.client.start_events()

    def test_reader_failure_is_reported_and_listener_exits(self):
        error = RuntimeError("reader failed")
        with patch.object(self.client, "watch_credential_events", side_effect=error):
            self.client.watch_events()
        self.client.on_event_error.assert_called_once_with(error, None)

    def test_default_error_hook_only_logs_exception_type(self):
        with self.assertLogs(
            "accounts.clients.python.jms_pam.client", level="WARNING"
        ) as logs:
            Client.on_event_error(
                self.client, RuntimeError("DO_NOT_LOG_SECRET"), self.subscription
            )
        self.assertIn("RuntimeError", str(logs.output))
        self.assertNotIn("DO_NOT_LOG_SECRET", str(logs.output))

    def test_clone_creates_fresh_subclass_state_without_starting_events(self):
        class ApplicationClient(Client):
            def __init__(self, *args, **options):
                super().__init__(*args, **options)
                self.credentials = {}

        with ApplicationClient(
            "https://testserver",
            app_id="app",
            app_secret="secret",
            instance_id="worker",
        ) as client:
            client.credentials["database"] = self.credential
            with client.clone() as clone:
                self.assertIsInstance(clone, ApplicationClient)
                self.assertFalse(clone.credentials)
                self.assertIsNone(clone._event_dispatcher)
                self.assertIsNot(clone.session, client.session)

    def test_application_example_confirms_only_after_successful_rotation_switch(self):
        path = (
            Path(__file__).parents[1]
            / "templates/accounts/credential_client/sdk_application_example.py.tpl"
        )
        module = ast.parse(path.read_text())
        # Load the downloadable example's definitions without starting its listener.
        module.body = [
            node
            for node in module.body
            if not isinstance(node, (ast.ImportFrom, ast.With))
        ]
        namespace = {"Client": Client}
        exec(compile(module, str(path), "exec"), namespace)  # noqa: S102
        namespace["apply_credential"] = Mock()
        with namespace["ApplicationClient"](
            "https://testserver",
            app_id="app",
            app_secret="secret",
            instance_id="worker",
        ) as client:
            client.confirm_credential = Mock()
            for mode in ("subscription", "alternating_rotation"):
                client.on_event(
                    {
                        "event": "snapshot",
                        "credentials": [{"key": "database", "credential_mode": mode}],
                    }
                )
                client.on_credential_changed(self.credential)
                if mode == "subscription":
                    client.confirm_credential.assert_not_called()
            client.confirm_credential.assert_called_once_with(
                key="database", revision=2, account_id="account"
            )
            client.confirm_credential.reset_mock()
            namespace["apply_credential"].side_effect = RuntimeError("switch failed")
            with self.assertRaises(RuntimeError):
                client.on_credential_changed(self.credential)
            client.confirm_credential.assert_not_called()
