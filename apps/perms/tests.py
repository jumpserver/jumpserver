from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase
from django.utils import timezone

from accounts.const import AliasAccount
from perms.const import ActionChoices
from perms.utils.asset_perm import PermAssetDetailUtil


class AssetPermissionExclusionTests(SimpleTestCase):
    def setUp(self):
        self.expires = timezone.now() + timedelta(days=1)
        self.asset = Mock()
        self.asset.all_valid_accounts.values_list.return_value = ['alice', 'bob']

    def permission(self, alias, actions):
        return SimpleNamespace(
            accounts=[alias], actions=actions, date_expired=self.expires,
        )

    def test_exclusions_only_remove_granted_actions(self):
        connect = ActionChoices.connect
        upload = ActionChoices.upload
        download = ActionChoices.download
        cases = [
            ('absent bit', download, connect, download),
            ('partial overlap', connect | download, connect | upload, download),
            ('subset', connect | download, connect, download),
            ('all granted bits', download, download, 0),
            ('higher absent bit', connect, download, connect),
            ('no grant', 0, connect, 0),
        ]
        for name, allowed, excluded, expected in cases:
            with self.subTest(name=name):
                permissions = [
                    self.permission('alice', allowed),
                    self.permission('!alice', excluded),
                ]
                actions, _ = PermAssetDetailUtil.parse_alias_action_date_expire(
                    permissions, self.asset,
                )
                self.assertEqual(actions, {'alice': expected} if expected else {})

    def test_exclusions_apply_after_all_accounts_expansion(self):
        permissions = [
            self.permission(AliasAccount.ALL, ActionChoices.download),
            self.permission('!alice', ActionChoices.connect),
        ]

        actions, expirations = PermAssetDetailUtil.parse_alias_action_date_expire(
            permissions, self.asset,
        )

        self.assertEqual(actions, {
            'alice': ActionChoices.download,
            'bob': ActionChoices.download,
        })
        self.assertEqual(expirations['alice'], [self.expires])

    def test_exclusions_apply_to_combined_policy_actions(self):
        permissions = [
            self.permission('alice', ActionChoices.connect),
            self.permission('alice', ActionChoices.download),
            self.permission('!alice', ActionChoices.connect),
            self.permission('!alice', ActionChoices.upload),
        ]

        actions, _ = PermAssetDetailUtil.parse_alias_action_date_expire(
            permissions, self.asset,
        )

        self.assertEqual(actions, {'alice': ActionChoices.download})

    def test_action_checks_do_not_accept_synthesized_permissions(self):
        util = PermAssetDetailUtil(SimpleNamespace(username='user'), 'asset-id')
        util.asset = self.asset
        util.user_asset_perms = [
            self.permission('alice', ActionChoices.download),
            self.permission('!alice', ActionChoices.connect),
        ]

        self.assertFalse(util.check_perm_actions('alice', [ActionChoices.connect]))
        self.assertFalse(util.check_perm_actions('alice', [ActionChoices.upload]))
        self.assertTrue(util.check_perm_actions('alice', [ActionChoices.download]))
