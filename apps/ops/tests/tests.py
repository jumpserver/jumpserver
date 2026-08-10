from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from ops.models.job import JMSPermedInventory, check_upload_permission
from perms.const import ActionChoices


class CheckUploadPermissionTestCase(SimpleTestCase):
    @patch('ops.models.job.PermAssetDetailUtil')
    def test_missing_account_keeps_no_account_error(self, perm_util_cls):
        host = check_upload_permission(
            {'error': 'No account available'},
            user=Mock(),
            asset=Mock(),
            account=None,
        )

        self.assertEqual(host['error'], 'No account available')
        perm_util_cls.assert_not_called()

    def test_classified_hosts_applies_callback_and_keeps_error_asset_id(self):
        asset = Mock(id='asset-id')
        platform = Mock()
        platform.automation.ansible_enabled = True
        platform.protocols.values.return_value = []
        inventory = JMSPermedInventory.__new__(JMSPermedInventory)
        inventory.assets = [asset]
        inventory.exclude_hosts = {}
        inventory.group_by_platform = Mock(return_value={platform: [asset]})
        inventory.set_platform_protocol_setting_to_asset = Mock(return_value=[])
        inventory.select_account = Mock(return_value=Mock())
        inventory.asset_to_host = Mock(return_value={'name': 'asset-1'})
        inventory.host_callback = Mock(
            side_effect=lambda host, **kwargs: {**host, 'error': 'denied'}
        )

        result = inventory.get_classified_hosts('/tmp')

        self.assertEqual(result['error'][0]['id'], 'asset-id')
        self.assertEqual(result['error'][0]['error'], 'denied')
        inventory.host_callback.assert_called_once()

    @patch('ops.models.job.PermAssetDetailUtil')
    def test_check_selected_account_upload_permission(self, perm_util_cls):
        asset = Mock()
        asset.name = 'asset-1'
        asset.protocols.values_list.return_value = ['ssh']
        account = Mock(username='fallback')
        perm_util = perm_util_cls.return_value
        perm_util.check_perm_protocols.return_value = True
        perm_util.check_perm_actions.return_value = False

        host = check_upload_permission(
            {}, user=Mock(), asset=asset, account=account
        )

        self.assertIn('error', host)
        self.assertIn('asset-1', str(host['error']))
        perm_util.check_perm_actions.assert_called_once_with(
            'fallback', [ActionChoices.upload.value]
        )
