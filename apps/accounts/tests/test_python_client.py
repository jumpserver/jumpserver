import json
from copy import deepcopy
from dataclasses import is_dataclass
from threading import Event
from unittest import TestCase
from unittest.mock import Mock, patch

import requests
from accounts.clients.python.jms_pam import Client, PAMError
from accounts.clients.python.jms_pam._events import EventStream
from accounts.clients.python.jms_pam.models import KnownRevision


class PythonClientTests(TestCase):
    def setUp(self):
        self.client = Client(
            "https://testserver/",
            app_id="application",
            app_secret="app-secret",
            instance_id="orders-worker-1",
            configuration_id="configuration",
        )
        self.addCleanup(self.client.close)
        self.payload = {
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

    def respond(self, payload, status=200):
        self.client.session.request = Mock(
            return_value=Mock(
                status_code=status,
                reason="test",
                json=Mock(return_value=payload),
            )
        )

    def test_keyword_calls_preserve_wire_payloads_and_typed_response(self):
        self.respond(self.payload)
        credential = self.client.get_credential(key="database")
        self.assertTrue(is_dataclass(credential))
        self.assertEqual(credential.account.username, "app")
        self.assertEqual(credential.asset.platform.type, "postgresql")
        self.assertEqual(credential.to_dict(), self.payload)
        self.assertEqual(
            self.client.session.request.call_args.kwargs["params"],
            {
                "key": "database",
                "instance_id": "orders-worker-1",
                "configuration_id": "configuration",
            },
        )
        self.respond({"key": "database", "revision": 2})
        confirmation = self.client.confirm_credential(
            key=credential.key,
            revision=credential.revision,
            account_id=credential.account.id,
        )
        self.assertEqual(confirmation.revision, 2)
        self.assertEqual(
            self.client.session.request.call_args.kwargs["json"],
            {
                "key": "database",
                "revision": 2,
                "account_id": "account",
                "instance_id": "orders-worker-1",
                "configuration_id": "configuration",
            },
        )

    def test_subscription_selects_by_account_id(self):
        self.respond(self.payload)
        self.client.get_credential(account_id="account")
        params = self.client.session.request.call_args.kwargs["params"]
        self.assertEqual(params["account_id"], "account")
        self.assertNotIn("key", params)

    def test_invalid_selectors_do_not_send_requests(self):
        self.client.session.request = Mock()
        for options in ({}, {"key": "database", "account_id": "account"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.client.get_credential(**options)
        self.client.session.request.assert_not_called()

    def test_confirmation_requires_an_exact_integer_revision(self):
        self.client.session.request = Mock()
        for revision in (None, "2", False, 0, -1):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                self.client.confirm_credential(
                    key="database",
                    account_id="account",
                    revision=revision,
                )
        self.client.session.request.assert_not_called()

    def test_secret_is_not_in_response_representation(self):
        self.respond(self.payload)
        credential = self.client.get_credential(key="database")
        self.assertNotIn("database-secret", repr(credential))
        self.assertNotIn("database-secret", repr(credential.account))
        self.assertNotIn("app-secret", repr(self.client))

    def test_http_and_response_errors_use_public_exception(self):
        self.respond({"code": "credential_not_authorized", "detail": "Denied"}, 403)
        with self.assertRaises(PAMError) as denied:
            self.client.get_credential(key="database")
        self.assertEqual(denied.exception.code, "credential_not_authorized")
        self.assertEqual(denied.exception.status_code, 403)
        self.respond({"code": {}, "detail": [], "request_id": []}, 403)
        with self.assertRaises(PAMError) as malformed:
            self.client.get_credential(key="database")
        self.assertEqual(malformed.exception.code, "HTTPError")
        self.assertEqual(malformed.exception.status_code, 403)
        self.respond({"key": "database"})
        with self.assertRaises(PAMError) as invalid:
            self.client.get_credential(key="database")
        self.assertEqual(invalid.exception.code, "ResponseError")
        self.client.session.request.side_effect = requests.Timeout("slow")
        with self.assertRaises(PAMError) as timeout:
            self.client.get_credential(key="database")
        self.assertEqual(timeout.exception.code, "NetworkError")

    def test_agent_sync_serializes_typed_revisions(self):
        self.respond(
            {
                "config_digest": "digest",
                "configuration": {"delivery_mode": "json"},
                "credentials": [
                    {
                        "key": "database",
                        "revision": 2,
                        "available": True,
                        "changed": False,
                    }
                ],
                "removed_keys": [],
                "date_last_synced": "now",
            }
        )
        result = self.client.sync_agent(
            config_digest="",
            credentials=[KnownRevision("database", 1)],
            delivered_credentials=[],
        )
        self.assertEqual(result.credentials[0].revision, 2)
        self.assertFalse(result.credentials[0].changed)
        data = self.client.session.request.call_args.kwargs["json"]
        self.assertEqual(data["credentials"], [{"key": "database", "revision": 1}])
        self.assertEqual(data["delivered_credentials"], [])

    def test_command_handler_runs_only_for_accepted_claims(self):
        self.client.session.request = Mock(
            side_effect=[
                Mock(status_code=200, json=Mock(return_value=payload))
                for payload in (
                    {"accepted": True, "status": "running"},
                    {"accepted": True, "status": "success"},
                    {"accepted": False, "status": "success"},
                )
            ]
        )
        event, handler = {"command_id": "command"}, Mock()
        self.client.execute_application_command(event, handler)
        self.client.execute_application_command(event, handler)
        handler.assert_called_once_with(event)
        self.assertEqual(
            [
                call.kwargs["json"]["status"]
                for call in self.client.session.request.call_args_list
            ],
            ["running", "success", "running"],
        )

    def test_handler_failure_reports_failed_command(self):
        self.respond({"accepted": True, "status": "running"})
        with self.assertRaises(RuntimeError):
            self.client.execute_application_command(
                {"command_id": "command"},
                Mock(side_effect=RuntimeError("failed")),
            )
        data = self.client.session.request.call_args.kwargs["json"]
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error_code"], "execution_failed")

    def test_event_iterator_acknowledges_before_yield_and_closes(self):
        event = {"event": "credential.updated", "event_id": "event"}
        connection = Mock(recv=Mock(return_value=json.dumps(event)))
        with patch(
            "accounts.clients.python.jms_pam._events.websocket.create_connection",
            return_value=connection,
        ):
            stream = self.client.watch_credential_events()
            self.assertEqual(next(stream), event)
            connection.send.assert_called_once_with(
                json.dumps(
                    {
                        "event": "received",
                        "event_id": "event",
                    }
                )
            )
            stream.close()
        connection.close.assert_called_once()

    def test_clone_owns_a_new_session_and_context_manager_closes_it(self):
        with self.client.clone() as cloned:
            self.assertIsNot(cloned.session, self.client.session)
            self.assertEqual(cloned.instance_id, self.client.instance_id)
            self.assertEqual(cloned.configuration_id, self.client.configuration_id)
            cloned.session.close = Mock()
        cloned.session.close.assert_called_once()

    def test_malformed_command_claim_never_runs_handler(self):
        handler = Mock()
        for accepted in ("false", 0, 1, None):
            with self.subTest(accepted=accepted):
                self.respond({"accepted": accepted, "status": "running"})
                with self.assertRaises(PAMError) as error:
                    self.client.execute_application_command(
                        {"command_id": "command"}, handler
                    )
                self.assertEqual(error.exception.code, "ResponseError")
        handler.assert_not_called()

    def test_response_revisions_must_be_exact_non_negative_integers(self):
        for revision in (True, "2", -1, 2.5):
            with self.subTest(revision=revision):
                payload = deepcopy(self.payload)
                payload["revision"] = revision
                self.respond(payload)
                with self.assertRaises(PAMError):
                    self.client.get_credential(key="database")
                self.client.session.request.return_value.close.assert_called_once()

    def test_failed_result_reporting_preserves_handler_exception(self):
        original = RuntimeError("application failed")
        self.client.report_application_command_result = Mock(
            side_effect=[
                Mock(accepted=True, status="running"),
                PAMError("NetworkError", "report failed"),
            ]
        )
        with self.assertLogs(level="WARNING"), self.assertRaises(RuntimeError) as error:
            self.client.execute_application_command(
                {"command_id": "command"}, Mock(side_effect=original)
            )
        self.assertIs(error.exception, original)

    def test_response_is_released_on_success_and_http_error(self):
        self.respond(self.payload)
        self.client.get_credential(key="database")
        self.client.session.request.return_value.close.assert_called_once()
        self.respond({"code": "denied", "detail": "Denied"}, status=403)
        with self.assertRaises(PAMError):
            self.client.get_credential(key="database")
        self.client.session.request.return_value.close.assert_called_once()

    def test_close_cancels_active_stream_and_prevents_session_reuse(self):
        event = {"event": "credential.updated", "event_id": "event"}
        connection = Mock(recv=Mock(return_value=json.dumps(event)))
        with patch(
            "accounts.clients.python.jms_pam._events.websocket.create_connection",
            return_value=connection,
        ) as connect:
            stream = self.client.watch_credential_events()
            self.assertEqual(next(stream), event)
            self.client.close()
            self.assertEqual(list(stream), [])
            connect.assert_called_once()
        connection.close.assert_called_once()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.client.get_credential(key="database")
        with self.assertRaisesRegex(RuntimeError, "closed"):
            next(self.client.watch_credential_events())

    def test_server_close_uses_backoff_and_closes_before_waiting(self):
        connections = [Mock(recv=Mock(return_value="")) for _ in range(3)]
        stream = EventStream("wss://testserver", Mock(return_value=[]), timeout=10)
        stop = Event()
        delays = []

        def wait(delay, _):
            connections[len(delays)].close.assert_called_once()
            delays.append(delay)
            if len(delays) == 3:
                stop.set()

        with (
            patch(
                "accounts.clients.python.jms_pam._events.websocket.create_connection",
                side_effect=connections,
            ),
            patch.object(stream, "_wait", side_effect=wait),
        ):
            self.assertEqual(list(stream.watch(stop)), [])
        self.assertEqual(delays, [1, 2, 4])

    def test_event_errors_do_not_log_server_supplied_secrets(self):
        stream = EventStream("wss://testserver", Mock(return_value=[]), timeout=10)
        connection = Mock(recv=Mock(side_effect=ValueError("DO_NOT_LOG_SECRET")))
        stop = Event()
        with (
            patch(
                "accounts.clients.python.jms_pam._events.websocket.create_connection",
                return_value=connection,
            ),
            patch.object(stream, "_wait", side_effect=lambda *_: stop.set()),
            self.assertLogs(level="WARNING") as logs,
        ):
            self.assertEqual(list(stream.watch(stop)), [])
        self.assertNotIn("DO_NOT_LOG_SECRET", str(logs.output))

    def test_endpoint_prefix_is_shared_by_http_and_event_stream(self):
        self.client.endpoint = "https://testserver/pam"
        self.respond(self.payload)
        self.client.get_credential(key="database")
        self.assertIn("/pam/api/", self.client.session.request.call_args.args[1])
        self.assertIn("/pam/ws/", self.client._event_stream_url())

    def test_constructor_rejects_invalid_endpoint_and_timeout(self):
        identity = dict(app_id="app", app_secret="secret", instance_id="worker")
        for endpoint in (
            "",
            "testserver",
            "ftp://testserver",
            "https://user:secret@host",
            "https://host?query=1",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                Client(endpoint, **identity)
        for timeout in (0, -1, True, "10", float("inf"), float("nan")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                Client("https://testserver", timeout=timeout, **identity)
