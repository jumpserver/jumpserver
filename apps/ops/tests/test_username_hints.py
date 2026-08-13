from datetime import timedelta
from types import SimpleNamespace

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from accounts.models import Account
from assets.const import Category, HostTypes, Protocol
from assets.models import Asset, Node, Platform
from ops.api.job import UsernameHintsAPI
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from perms.const import ActionChoices
from perms.models import AssetPermission
from users.models import User


class UsernameHintsPermissionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, _ = Organization.objects.get_or_create(
            id=Organization.DEFAULT_ID,
            defaults={'name': 'DEFAULT', 'builtin': True},
        )
        cls.user = User.objects.create(
            username='file-transfer-user',
            name='File transfer user',
        )
        cls.platform = Platform.objects.create(
            name='File transfer permission test',
            category=Category.HOST,
            type=HostTypes.LINUX,
        )

    def create_asset(self, name, protocol=Protocol.ssh):
        with tmp_to_root_org():
            asset = Asset.objects.create(
                org_id=self.org.id,
                name=name,
                address=f'{name}.example.com',
                platform=self.platform,
            )
            asset.protocols.create(name=protocol, port=22)
        return asset

    def create_account(self, asset, username):
        with tmp_to_root_org():
            return Account.objects.create(
                org_id=self.org.id,
                asset=asset,
                name=username,
                username=username,
            )

    def grant(self, name, asset, account, actions, protocols=None):
        with tmp_to_root_org():
            permission = AssetPermission.objects.create(
                org_id=self.org.id,
                name=name,
                accounts=[account],
                protocols=protocols or list(
                    asset.protocols.values_list('name', flat=True)
                ),
                actions=actions,
                date_start=timezone.now() - timedelta(minutes=1),
                date_expired=timezone.now() + timedelta(days=1),
            )
            permission.users.add(self.user)
            permission.assets.add(asset)

    def get_hints(self, asset, action=None):
        assets = asset if isinstance(asset, list) else [asset]
        data = {
            'nodes': [],
            'assets': [str(item.id) for item in assets],
            'query': '',
        }
        if action:
            data['action'] = action
        request = SimpleNamespace(user=self.user, data=data)
        with tmp_to_org(self.org):
            response = UsernameHintsAPI().post(request)
        return list(response.data)

    def test_upload_hints_exclude_accounts_without_upload_permission(self):
        asset = self.create_asset('upload-asset')
        self.create_account(asset, 'upload-user')
        self.create_account(asset, 'connect-only-user')
        self.create_account(asset, 'ungranted-user')
        self.grant(
            'Upload account permission',
            asset,
            'upload-user',
            ActionChoices.connect.value | ActionChoices.upload.value,
        )
        self.grant(
            'Connect account permission',
            asset,
            'connect-only-user',
            ActionChoices.connect.value,
        )
        self.grant(
            'Virtual upload account permission',
            asset,
            '@INPUT',
            ActionChoices.upload.value,
        )

        hints = self.get_hints(asset, action='upload')

        self.assertEqual(hints, [{'username': 'upload-user', 'total': 1}])

    def test_upload_hints_exclude_assets_without_transfer_protocols(self):
        asset = self.create_asset('telnet-asset', protocol=Protocol.telnet)
        self.create_account(asset, 'telnet-user')
        self.grant(
            'Telnet upload permission',
            asset,
            'telnet-user',
            ActionChoices.upload.value,
        )

        hints = self.get_hints(asset, action='upload')

        self.assertEqual(hints, [])

    def test_upload_hints_filter_each_permission_by_protocol(self):
        asset = self.create_asset('mixed-protocol-asset')
        self.create_account(asset, 'ssh-user')
        self.create_account(asset, 'telnet-only-user')
        self.grant(
            'SSH upload permission',
            asset,
            'ssh-user',
            ActionChoices.upload.value,
            protocols=[Protocol.ssh],
        )
        self.grant(
            'Telnet upload permission',
            asset,
            'telnet-only-user',
            ActionChoices.upload.value,
            protocols=[Protocol.telnet],
        )

        hints = self.get_hints(asset, action='upload')

        self.assertEqual(hints, [{'username': 'ssh-user', 'total': 1}])

    def test_default_hints_keep_connect_permission_semantics(self):
        asset = self.create_asset('quick-job-asset')
        self.create_account(asset, 'connect-user')
        self.create_account(asset, 'upload-only-user')
        self.grant(
            'Connect account permission',
            asset,
            'connect-user',
            ActionChoices.connect.value,
        )
        self.grant(
            'Upload account permission',
            asset,
            'upload-only-user',
            ActionChoices.upload.value,
        )

        hints = self.get_hints(asset)

        self.assertEqual(hints, [{'username': 'connect-user', 'total': 1}])

    def test_query_count_does_not_grow_per_selected_asset(self):
        small_asset = self.create_asset('query-small')
        self.create_account(small_asset, 'small-user')
        self.grant(
            'Small query permission',
            small_asset,
            'small-user',
            ActionChoices.upload.value,
        )

        large_assets = []
        for index in range(8):
            asset = self.create_asset(f'query-large-{index}')
            username = f'large-user-{index}'
            self.create_account(asset, username)
            self.grant(
                f'Large query permission {index}',
                asset,
                username,
                ActionChoices.upload.value,
            )
            large_assets.append(asset)

        def get_usernames(assets):
            return UsernameHintsAPI.get_permed_account_usernames(
                self.user,
                assets,
                ActionChoices.upload.value,
                UsernameHintsAPI.upload_protocols,
            )

        with tmp_to_org(self.org):
            with CaptureQueriesContext(connection) as small_queries:
                get_usernames([small_asset])
            with CaptureQueriesContext(connection) as large_queries:
                get_usernames(large_assets)

        self.assertLessEqual(len(large_queries), len(small_queries) + 2)
        self.assertLessEqual(len(large_queries), 20)

    def test_node_permission_is_applied_to_child_asset(self):
        asset = self.create_asset('node-authorized-asset')
        self.create_account(asset, 'node-upload-user')
        with tmp_to_org(self.org):
            node = Node.org_root().create_child('File transfer')
            child = node.create_child('Linux')
            asset.nodes.add(child)
        with tmp_to_root_org():
            permission = AssetPermission.objects.create(
                org_id=self.org.id,
                name='Node upload permission',
                accounts=['node-upload-user'],
                protocols=[Protocol.ssh],
                actions=ActionChoices.upload.value,
                date_start=timezone.now() - timedelta(minutes=1),
                date_expired=timezone.now() + timedelta(days=1),
            )
            permission.users.add(self.user)
            permission.nodes.add(node)

        hints = self.get_hints(asset, action='upload')

        self.assertEqual(hints, [
            {'username': 'node-upload-user', 'total': 1},
        ])

    def test_all_account_alias_honors_explicit_exclusion(self):
        asset = self.create_asset('all-account-asset')
        self.create_account(asset, 'allowed-user')
        self.create_account(asset, 'excluded-user')
        self.grant(
            'All upload accounts',
            asset,
            '@ALL',
            ActionChoices.upload.value,
        )
        self.grant(
            'Exclude upload account',
            asset,
            '!excluded-user',
            ActionChoices.upload.value,
        )

        hints = self.get_hints(asset, action='upload')

        self.assertEqual(hints, [
            {'username': 'allowed-user', 'total': 1},
        ])
