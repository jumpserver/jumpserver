from collections import OrderedDict

from django.test import SimpleTestCase
from django.utils.translation import override

from accounts.automations.backup_account.handlers import AssetAccountHandler
from accounts.models import Account
from accounts.serializers import AccountSecretSerializer
from assets.models import Asset, Platform


class AccountBackupExportTests(SimpleTestCase):
    def setUp(self):
        self.enterContext(override('en'))
        self.headers = AssetAccountHandler.get_header_fields(AccountSecretSerializer())
        self.data = {
            'id': 'account-id', 'name': 'root-account', 'username': 'root',
            'asset': {
                'id': 'asset-id', 'name': 'server-01', 'address': '192.0.2.10',
                'type': {'value': 'linux', 'label': 'Linux'},
                'category': {'value': 'host', 'label': 'Host'},
                'platform': {'id': 'platform-id', 'name': 'Linux platform'},
                'auto_config': {'ansible_enabled': True},
            },
            'asset_address': '192.0.2.10',
            'secret_type': {'value': 'password', 'label': 'Password'},
            'secret': 'example-password', 'privileged': False,
            'passphrase': 'excluded-passphrase', 'params': {'excluded': True},
        }

    def test_asset_identity_does_not_replace_account_identity(self):
        for mapping in (dict, OrderedDict):
            with self.subTest(mapping=mapping.__name__):
                data = {**self.data, 'asset': mapping(self.data['asset'])}
                row = AssetAccountHandler.create_row(data, self.headers)
                self.assertEqual(row['ID'], 'account-id')
                self.assertEqual(row['Name'], 'root-account')
                self.assertEqual(row['Asset Id'], 'asset-id')
                self.assertEqual(row['Asset Name'], 'server-01')
                self.assertEqual(row['Asset Address'], '192.0.2.10')
                self.assertEqual(row['Asset IP'], '192.0.2.10')
                self.assertEqual(row['Asset Type'], 'Linux')
                self.assertEqual(row['Asset Category'], 'Host')
                self.assertEqual(row[self.headers['secret_type']], 'Password')
                self.assertEqual(row[self.headers['privileged']], 'False')
                self.assertEqual(row[self.headers['secret']], 'example-password')
                self.assertNotIn('excluded-passphrase', row.values())
                self.assertNotIn('platform-id', row.values())
                self.assertNotIn('asset.platform', self.headers)
                self.assertNotIn('asset.auto_config', self.headers)
                self.assertNotIn('params', self.headers)

    def test_asset_fields_from_real_serializer(self):
        asset = Asset(name='server-01', address='192.0.2.10', platform=Platform(type='linux'))
        serializer = AccountSecretSerializer(Account(name='root-account', asset=asset))
        for name in list(serializer.fields):
            if name not in ('id', 'name', 'asset', 'asset_address'):
                serializer.fields.pop(name)
        for name in serializer.fields['asset'].Meta.exclude_backup_fields:
            serializer.fields['asset'].fields.pop(name)

        headers = AssetAccountHandler.get_header_fields(serializer)
        row = AssetAccountHandler.create_row(serializer.data, headers)
        self.assertEqual(row['Name'], 'root-account')
        self.assertEqual(row['Asset Name'], 'server-01')
        self.assertEqual(row['Asset Address'], '192.0.2.10')
        self.assertEqual(row['Asset IP'], '192.0.2.10')

    def test_missing_or_null_asset_fields_are_blank(self):
        for asset in (None, {}, {'name': None, 'address': None}):
            with self.subTest(asset=asset):
                data = {**self.data, 'asset': asset, 'asset_address': None}
                row = AssetAccountHandler.create_row(data, self.headers)
                self.assertEqual(row['Name'], 'root-account')
                self.assertEqual(row['Asset Name'], '')
                self.assertEqual(row['Asset Address'], '')
                self.assertEqual(row['Asset IP'], '')

    def test_split_secrets_keep_asset_values_and_column_alignment(self):
        for section, expected in (('front', 'example-********'), ('back', '********password')):
            with self.subTest(section=section):
                data = {**self.data}
                AssetAccountHandler.handler_secret([data], section)
                rows = AssetAccountHandler.add_rows([data], self.headers, 'Linux')['Linux']
                row = dict(zip(*rows))
                self.assertEqual(len(rows[0]), len(rows[1]))
                self.assertEqual(row[self.headers['secret']], expected)
                self.assertEqual(row['Asset Name'], 'server-01')
                self.assertEqual(row['Asset Address'], '192.0.2.10')
