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
        Key=key, Revision=revision,
        Asset=SimpleNamespace(Id='asset-1', Name='database', Address='127.0.0.1'),
        Account=SimpleNamespace(
            Id=account_id, Name=account_id, Username=account_id,
            SecretType='password', Secret=secret,
        ),
    )


class FileApplicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / 'config.json'

    def test_subscription_updates_only_changed_accounts_and_prunes_snapshot(self):
        client = Mock()
        client.GetCredential.side_effect = [
            response('policy:account-1', 1, 'account-1', 'first'),
            response('policy:account-2', 2, 'account-2', 'second'),
        ]
        snapshot = {'event': 'snapshot', 'credentials': [
            {'credential_mode': 'subscription', 'account_id': 'account-1', 'revision': 1},
        ]}
        handle_subscription(client, self.output, snapshot)
        self.assertEqual(os.stat(self.output).st_mode & 0o777, 0o600)
        self.assertEqual(client.GetCredential.call_count, 1)
        handle_subscription(client, self.output, snapshot)
        self.assertEqual(client.GetCredential.call_count, 1)

        handle_subscription(client, self.output, {
            'event': 'credential.updated', 'credential_mode': 'subscription',
            'account_id': 'account-2', 'revision': 2,
        })
        self.assertEqual(set(load_local(self.output, 'subscription')['credentials']), {
            'account-1', 'account-2',
        })
        handle_subscription(client, self.output, snapshot)
        self.assertEqual(set(load_local(self.output, 'subscription')['credentials']), {'account-1'})

    def test_rotation_confirms_only_after_file_was_written_and_read_back(self):
        client = Mock()
        client.GetCredential.return_value = response('policy', 4, 'account-2', 'new-secret')

        def check_file(_):
            data = json.loads(self.output.read_text(encoding='utf-8'))
            self.assertEqual(data['credentials']['policy']['account']['secret'], 'new-secret')

        client.ConfirmCredential.side_effect = check_file
        handle_rotation(client, self.output, {
            'event': 'credential.updated', 'credential_mode': 'alternating_rotation',
            'credential_key': 'policy', 'revision': 4,
        }, {'policy'}, confirm=True)
        self.assertEqual(client.ConfirmCredential.call_count, 1)
        self.assertEqual(os.stat(self.output).st_mode & 0o777, 0o600)

        client.ConfirmCredential.reset_mock()
        handle_rotation(client, self.output, {
            'event': 'snapshot', 'credentials': [
                {'credential_mode': 'alternating_rotation', 'key': 'policy', 'revision': 4},
            ],
        }, {'policy'})
        client.ConfirmCredential.assert_not_called()

        with patch('file_apps.rotation.save_local', side_effect=OSError('disk full')):
            client.GetCredential.return_value = response('policy', 5, 'account-1', 'next-secret')
            with self.assertRaises(OSError):
                handle_rotation(client, self.output, {
                    'event': 'credential.updated', 'credential_mode': 'alternating_rotation',
                    'credential_key': 'policy', 'revision': 5,
                }, {'policy'}, confirm=True)
        client.ConfirmCredential.assert_not_called()


if __name__ == '__main__':
    unittest.main()
