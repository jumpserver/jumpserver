from threading import Event, Thread
from unittest import TestCase
from unittest.mock import Mock, patch

import requests
import websocket
from accounts.clients.python.jms_pam import PAMError
from accounts.clients.python.jms_pam._event_dispatcher import EventDispatcher
from accounts.clients.python.jms_pam._events import EventStream
from accounts.tests import test_python_client as test_helpers


class PythonLatestCredentialTests(TestCase):
    setUp = test_helpers.PythonClientTests.setUp
    respond = test_helpers.PythonClientTests.respond

    def prime(self):
        self.respond(self.payload)
        value = self.client.get_credential(key="database")
        self.assertFalse(value.from_local)
        return value

    def outage(self):
        self.client.session.request.side_effect = requests.Timeout("temporary")

    def test_network_timeout_and_5xx_return_marked_local_credential(self):
        live = self.prime()
        self.outage()
        retained = self.client.get_credential(key="database")
        self.assertTrue(retained.from_local)
        self.assertEqual(retained.to_dict(), live.to_dict())
        self.assertNotIn("database-secret", repr(retained))
        self.respond({"code": "unavailable"}, 503)
        self.assertTrue(self.client.get_credential(key="database").from_local)

    def test_fresh_request_and_other_selector_do_not_use_retained_credentials(self):
        self.prime()
        self.outage()
        for options in (
            {"key": "database", "allow_local_fallback": False},
            {"account_id": "account"},
        ):
            with self.subTest(options=options), self.assertRaises(PAMError):
                self.client.get_credential(**options)

    def test_application_pull_never_uses_cached_secret_during_outage(self):
        self.respond({**self.payload, "key": "account:account"})
        self.client.get_credential(account_id="account")
        self.client._reconcile_latest_credentials({"event": "snapshot", "credentials": []})
        self.outage()
        with self.assertRaises(PAMError):
            self.client.get_credential(account_id="account")

    def test_latest_credential_does_not_expire(self):
        self.prime()
        self.outage()
        with patch("time.monotonic", return_value=10**12):
            self.assertTrue(self.client.get_credential(key="database").from_local)
        self.assertTrue(self.client._latest_credentials)

    def test_access_denial_and_upgrade_clear_retained_credentials(self):
        for status in (400, 401, 403, 404, 426):
            with self.subTest(status=status):
                self.prime()
                self.respond(
                    {
                        "code": "client_upgrade_required"
                        if status == 426
                        else "credential_not_found"
                        if status == 400
                        else "denied"
                    },
                    status,
                )
                with self.assertRaises(PAMError):
                    self.client.get_credential(key="database")
                self.outage()
                with self.assertRaises(PAMError):
                    self.client.get_credential(key="database")

    def test_invalid_successful_response_does_not_use_cache(self):
        self.prime()
        self.respond({"key": "database"})
        with self.assertRaises(PAMError) as error:
            self.client.get_credential(key="database")
        self.assertEqual(error.exception.code, "ResponseError")

    def test_identity_denial_on_other_api_also_clears_retained_credentials(self):
        self.prime()
        self.respond({"code": "client_disabled"}, 403)
        with self.assertRaises(PAMError):
            self.client.list_application_commands()
        self.outage()
        with self.assertRaises(PAMError):
            self.client.get_credential(key="database")

    def test_snapshot_scope_changes_remove_retained_credentials(self):
        for event in (
            {"event": "snapshot", "credentials": []},
            {
                "event": "snapshot",
                "credentials": [{"key": "other-policy", "account_id": "account"}],
            },
            {"event": "credential.revoked"},
            {"event": "snapshot", "credentials": [{"key": [], "account_id": {}}]},
        ):
            with self.subTest(event=event):
                self.prime()
                self.client._reconcile_latest_credentials(event)
                self.outage()
                with self.assertRaises(PAMError):
                    self.client.get_credential(key="database")

    def test_snapshot_keeps_authorized_credentials_and_clone_starts_empty(self):
        self.prime()
        self.client._reconcile_latest_credentials(
            {"event": "snapshot", "credentials": [{"key": "database"}]}
        )
        self.outage()
        self.assertTrue(self.client.get_credential(key="database").from_local)
        clone = self.client.clone()
        self.addCleanup(clone.close)
        clone.session.request = Mock(side_effect=requests.Timeout())
        with self.assertRaises(PAMError):
            clone.get_credential(key="database")

    def test_revoked_inflight_response_cannot_repopulate_local_state(self):
        entered, release = Event(), Event()
        self.respond(self.payload)
        response = self.client.session.request.return_value

        def request(*args, **kwargs):
            entered.set()
            release.wait(2)
            return response

        self.client.session.request.side_effect = request
        worker = Thread(target=lambda: self.client.get_credential(key="database"))
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            self.client._reconcile_latest_credentials({"event": "credential.revoked"})
        finally:
            release.set()
            worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertFalse(self.client._latest_credentials)

    def test_configuration_notice_keeps_latest_until_scope_is_reconciled(self):
        self.prime()
        self.client._reconcile_latest_credentials({"event": "configuration.updated"})
        self.outage()
        self.assertTrue(self.client.get_credential(key="database").from_local)

    def test_policy_revocation_removes_subscription_account_alias(self):
        self.respond({**self.payload, "key": "database:account"})
        self.client.get_credential(account_id="account")
        self.client._reconcile_latest_credentials(
            {"event": "credential.revoked", "credential_key": "database"}
        )
        self.outage()
        with self.assertRaises(PAMError):
            self.client.get_credential(account_id="account")

    def test_online_refresh_replaces_latest_and_rejects_older_revision(self):
        self.prime()
        updated = {
            **self.payload,
            "revision": 3,
            "account": {**self.payload["account"], "secret": "new-password"},
        }
        self.respond(updated)
        self.assertFalse(self.client.get_credential(key="database").from_local)
        self.respond(self.payload)
        with self.assertRaises(PAMError):
            self.client.get_credential(key="database")
        self.outage()
        retained = self.client.get_credential(key="database")
        self.assertEqual(retained.revision, 3)
        self.assertEqual(retained.account.secret, "new-password")

    def test_update_events_fetch_latest_without_business_fetch_and_failed_refresh_retains_it(
        self,
    ):
        self.prime()
        updated = {
            **self.payload,
            "revision": 3,
            "account": {**self.payload["account"], "secret": "new-password"},
        }
        self.respond(updated)
        self.client.on_event_error = Mock()
        self.client.on_credential_changed = Mock(
            side_effect=RuntimeError("application unavailable")
        )
        dispatcher = EventDispatcher(self.client)
        event = {
            "event": "credential.updated",
            "credential_mode": "alternating_rotation",
            "credential_key": "database",
            "revision": 3,
        }
        dispatcher._dispatch(event)
        self.assertEqual(
            self.client.on_credential_changed.call_args.args[0].revision, 3
        )
        self.client.on_credential_changed.reset_mock()
        self.outage()
        dispatcher._dispatch({**event, "revision": 4})
        self.client.on_credential_changed.assert_not_called()
        retained = self.client.get_credential(key="database")
        self.assertEqual(retained.account.secret, "new-password")
        self.assertEqual(retained.revision, 3)
        self.assertTrue(retained.from_local)

    def test_silent_connection_reconnects_with_fresh_headers(self):
        silent, recovered = Mock(), Mock()
        silent.recv.side_effect = websocket.WebSocketTimeoutException()
        recovered.recv.return_value = '{"event":"snapshot","credentials":[]}'
        headers = Mock(
            side_effect=[["Authorization: first"], ["Authorization: second"]]
        )
        stream = EventStream("wss://testserver", headers, 10)
        with (
            patch(
                "accounts.clients.python.jms_pam._events.websocket.create_connection",
                side_effect=[silent, recovered],
            ) as connect,
            patch(
                "accounts.clients.python.jms_pam._events.monotonic",
                side_effect=[0, 10, 31, 40, 41],
            ),
            patch.object(stream, "_wait"),
        ):
            events = stream.watch()
            self.assertEqual(next(events)["event"], "snapshot")
            events.close()
        self.assertEqual(connect.call_count, 2)
        self.assertEqual(connect.call_args.kwargs["header"], ["Authorization: second"])
        silent.send.assert_called_once()
        silent.close.assert_called_once()
