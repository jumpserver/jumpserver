from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils.translation import override
from rest_framework.exceptions import PermissionDenied

from acls.models.login_asset_acl import LoginAssetPolicy
from ops.api.job import LoginAssetACLCheckMixin
from ops.models.job import JobExecution


class LoginAssetACLMessageTests(SimpleTestCase):
    def setUp(self):
        self.asset = SimpleNamespace(name='alpine-3.19', address='172.18.252.4')
        self.user = SimpleNamespace(username='jym')
        self.execution = SimpleNamespace(
            creator=self.user, inventory=SimpleNamespace(assets=[self.asset]),
            current_job=SimpleNamespace(runas='jym'),
        )
        self.messages = {
            'zh-hans': '登录控制策略已拒绝访问资产 alpine-3.19（172.18.252.4），请联系管理员。',
            'en': 'Access to asset alpine-3.19 (172.18.252.4) is denied by a login control policy. '
                  'Contact your administrator.',
        }

    def test_api_denial_is_localized_without_policy_details(self):
        with patch('ops.api.job.match_rejected_login_asset_acl',
                   return_value=(self.asset, LoginAssetPolicy(()))):
            for language, expected in self.messages.items():
                with self.subTest(language=language), override(language):
                    with self.assertRaises(PermissionDenied) as error:
                        LoginAssetACLCheckMixin().check_login_asset_acls(
                            self.user, [self.asset], 'jym', '127.0.0.1'
                        )
                    self.assertEqual(str(error.exception.detail), expected)

    def test_scheduled_job_error_and_log_use_the_same_localized_message(self):
        with patch('ops.models.job.match_rejected_login_asset_acl',
                   return_value=(self.asset, LoginAssetPolicy(()))):
            for language, expected in self.messages.items():
                with self.subTest(language=language), override(language), redirect_stdout(StringIO()) as output:
                    with self.assertRaises(Exception) as error:
                        JobExecution.check_login_asset_acls(self.execution)
                    self.assertEqual(str(error.exception), expected)
                    self.assertEqual(output.getvalue(), f'\033[31m{expected}\033[0m\n')

    def test_allowed_assets_are_unchanged(self):
        with patch('ops.api.job.match_rejected_login_asset_acl', return_value=(None, None)), \
                patch('ops.models.job.match_rejected_login_asset_acl', return_value=(None, None)), \
                redirect_stdout(StringIO()) as output:
            self.assertIsNone(LoginAssetACLCheckMixin().check_login_asset_acls(
                self.user, [self.asset], 'jym', '127.0.0.1'
            ))
            self.assertIsNone(JobExecution.check_login_asset_acls(self.execution))
            self.assertEqual(output.getvalue(), '')
