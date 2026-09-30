"""Verify the Python baseline against the same wire contract as other SDKs."""

import json
import os
import sys
import unittest
from contextlib import closing
from pathlib import Path
from threading import Timer
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from jms_pam import Client, PAMError
from jms_pam.models import KnownRevision


@unittest.skipUnless(os.environ.get("JMS_TEST_ENDPOINT"), "Run through tests/run.py")
class PythonContractTests(unittest.TestCase):
    def client(self, instance="python-contract", **options):
        return Client(
            os.environ["JMS_TEST_ENDPOINT"],
            app_id="contract-app",
            app_secret="contract-secret",
            org_id="contract-org",
            instance_id=instance,
            **options,
        )

    def test_signed_credential_and_confirmation(self):
        with self.client() as client:
            credential = client.get_credential(key="db /中文?&=")
            self.assertEqual(credential.key, "db /中文?&=")
            self.assertEqual(credential.account.username, "app")
            self.assertNotIn("DO_NOT_LOG_SECRET", repr(credential))
            self.assertEqual(client.get_credential(account_id="account").revision, 2)
            self.assertEqual(
                client.confirm_credential(
                    key="db", revision=2, account_id="account"
                ).revision,
                2,
            )

    def test_errors_and_validation(self):
        with self.client() as client:
            for key, status in [("forbidden", 403), ("upgrade", 426)]:
                with self.assertRaises(PAMError) as failure:
                    client.get_credential(key=key)
                self.assertEqual(failure.exception.status_code, status)
            for key in ["invalid-json", "invalid-revision"]:
                with self.assertRaises(PAMError):
                    client.get_credential(key=key)
            with self.assertRaises(ValueError):
                client.get_credential(key="db", account_id="account")

    def test_agent_sync(self):
        with self.client(source="jms-pam-agent") as client:
            result = client.sync_agent(
                credentials=[KnownRevision("db", 1)],
                delivered_credentials=[KnownRevision("db", 1)],
            )
            self.assertTrue(result.credentials[0].available)
            self.assertEqual(result.scope["credential_keys"], ["db"])
            with self.assertRaises(PAMError):
                client.sync_agent(
                    credentials=[],
                    delivered_credentials=[],
                    sync_error="invalid-flag",
                )

    def test_command_claim_and_original_error(self):
        with self.client() as client:
            commands = client.list_application_commands()
            called = []
            self.assertTrue(
                client.execute_application_command(commands[0], called.append).accepted
            )
            self.assertEqual(len(called), 1)
            duplicate = {**commands[0], "command_id": "duplicate"}
            self.assertFalse(
                client.execute_application_command(duplicate, called.append).accepted
            )
            self.assertEqual(len(called), 1)
            original = RuntimeError("Application switch failed")

            def fail(_):
                raise original

            with self.assertRaises(RuntimeError) as failure:
                client.execute_application_command(
                    {**commands[0], "command_id": "report-failure"},
                    fail,
                )
            self.assertIs(failure.exception, original)

    def test_events_reconnect_receipts_and_clone(self):
        instance = "python-events"
        client = self.client(instance)
        clone = client.clone()
        stop = Timer(8, client.close)
        stop.start()
        try:
            events = []
            with closing(client.watch_credential_events()) as stream:
                for event in stream:
                    events.append(event)
                    if (
                        event["event"] == "snapshot"
                        and event["credentials"][0]["revision"] == 3
                    ):
                        break
            self.assertEqual(
                [event["event"] for event in events],
                [
                    "snapshot",
                    "credential.updated",
                    "future.notification",
                    "snapshot",
                ],
            )
            self.assertEqual(events[2]["future_payload"]["notice"], "preserved")
            endpoint = os.environ["JMS_TEST_ENDPOINT"].removesuffix("/prefix")
            with urlopen(endpoint + "/__stats") as response:
                stats = json.load(response)
            self.assertFalse(stats["failures"])
            received = {
                item["eventId"]
                for item in stats["receipts"]
                if item["instance"] == instance
            }
            self.assertTrue({"updated-1", "future-1"}.issubset(received))
            client.close()
            self.assertEqual(clone.get_credential(key="db").revision, 2)
        finally:
            stop.cancel()
            client.close()
            clone.close()


if __name__ == "__main__":
    unittest.main()
