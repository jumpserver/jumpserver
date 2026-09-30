import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from file_apps.common import load_local
from file_apps.rotation import handle_event as handle_rotation
from file_apps.subscription import handle_event as handle_subscription


def response(key, revision, account_id, secret):
    return SimpleNamespace(
        key=key,
        revision=revision,
        asset=SimpleNamespace(id="asset-1", name="database", address="127.0.0.1"),
        account=SimpleNamespace(
            id=account_id,
            name=account_id,
            username=account_id,
            secret_type="password",
            secret=secret,
        ),
    )


class FileApplicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "config.json"

    def test_subscription_updates_only_changed_accounts_and_prunes_snapshot(self):
        client = Mock()
        client.get_credential.side_effect = [
            response("policy:account-1", 1, "account-1", "first"),
            response("policy:account-2", 2, "account-2", "second"),
        ]
        snapshot = {
            "event": "snapshot",
            "credentials": [
                {
                    "credential_mode": "subscription",
                    "credential_key": "policy",
                    "account_id": "account-1",
                    "revision": 1,
                },
            ],
        }
        handle_subscription(client, self.output, snapshot)
        self.assertEqual(os.stat(self.output).st_mode & 0o777, 0o600)
        self.assertEqual(client.get_credential.call_count, 1)
        client.get_credential.assert_called_with(
            key="policy:account-1", allow_local_fallback=False
        )
        handle_subscription(client, self.output, snapshot)
        self.assertEqual(client.get_credential.call_count, 1)

        handle_subscription(
            client,
            self.output,
            {
                "event": "credential.updated",
                "credential_mode": "subscription",
                "credential_key": "policy",
                "account_id": "account-2",
                "revision": 2,
            },
        )
        client.get_credential.assert_called_with(
            key="policy:account-2", allow_local_fallback=False
        )
        self.assertEqual(
            set(load_local(self.output, "subscription")["credentials"]),
            {
                "account-1",
                "account-2",
            },
        )
        handle_subscription(client, self.output, snapshot)
        self.assertEqual(
            set(load_local(self.output, "subscription")["credentials"]), {"account-1"}
        )

    def test_rotation_confirms_only_after_file_was_written_and_read_back(self):
        client = Mock()
        client.get_credential.return_value = response(
            "policy", 4, "account-2", "new-secret"
        )

        def check_file(**_):
            data = json.loads(self.output.read_text(encoding="utf-8"))
            self.assertEqual(
                data["credentials"]["policy"]["account"]["secret"], "new-secret"
            )

        client.confirm_credential.side_effect = check_file
        handle_rotation(
            client,
            self.output,
            {
                "event": "credential.updated",
                "credential_mode": "alternating_rotation",
                "credential_key": "policy",
                "revision": 4,
            },
            {"policy"},
            confirm=True,
        )
        self.assertEqual(client.confirm_credential.call_count, 1)
        self.assertEqual(os.stat(self.output).st_mode & 0o777, 0o600)

        client.confirm_credential.reset_mock()
        handle_rotation(
            client,
            self.output,
            {
                "event": "snapshot",
                "credentials": [
                    {
                        "credential_mode": "alternating_rotation",
                        "key": "policy",
                        "revision": 4,
                    },
                ],
            },
            {"policy"},
        )
        client.confirm_credential.assert_not_called()

        with patch("file_apps.rotation.save_local", side_effect=OSError("disk full")):
            client.get_credential.return_value = response(
                "policy", 5, "account-1", "next-secret"
            )
            with self.assertRaises(OSError):
                handle_rotation(
                    client,
                    self.output,
                    {
                        "event": "credential.updated",
                        "credential_mode": "alternating_rotation",
                        "credential_key": "policy",
                        "revision": 5,
                    },
                    {"policy"},
                    confirm=True,
                )
        client.confirm_credential.assert_not_called()


if __name__ == "__main__":
    unittest.main()
