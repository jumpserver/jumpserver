"""Certificate binding orchestration, permissions and pending-login regressions."""
import time
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from authentication.backends.ukey import api, pending
from authentication.backends.ukey.configuration import REVISION
from authentication.backends.ukey.exceptions import UKeyAuthError
from authentication.backends.ukey.forms import CertificateUKeyLoginForm, VCTKSCertificateLoginForm
from authentication.backends.ukey.forms import UKeyLoginForm
from authentication.backends.ukey.providers import get_provider
from authentication.backends.ukey.views import UKeyLoginView
from authentication.errors import SessionEmptyError
from authentication.tests.test_ukey_vctk_s_config import snapshot


class VCTKSBindingTests(SimpleTestCase):
    def setUp(self):
        self.state = snapshot()
        self.user = SimpleNamespace(pk='target-user')
        self.identity = {
            'provider': 'vctk_s', 'issuer_fingerprint': 'a' * 64,
            'certificate_fingerprint': 'b' * 64, 'serial_number': '1234',
        }
        self.view = api.UKeyCertificateBindingAPI()
        self.view.get_object = MagicMock(return_value=self.user)
        self.view.get_queryset = MagicMock()
        self.view.check_object_permissions = MagicMock()
        self.payload = {
            'action': 'bind', 'revision': self.state[REVISION],
            'challenge_id': 'c' * 43, 'cert': 'certificate',
            'signature': 'p' * 5000, 'hardware_serial': 'device-serial',
        }
        self.request = SimpleNamespace(data=self.payload)
        self.record = {'code': 'ab' * 32, 'binding_version': ''}
        patches = {
            'snapshot': patch.object(api, 'get_snapshot', side_effect=lambda: self.state),
            'consume': patch.object(api.challenges, 'consume', return_value=(self.record, self.state)),
            'verify': patch.object(api, 'verify_identity', return_value=self.identity),
            'lock': patch.object(api, 'locked_snapshot', side_effect=lambda revision: nullcontext(self.state)),
            'version': patch.object(api, 'binding_version', return_value=''),
            'users': patch.object(api.User, 'objects'),
            'bindings': patch.object(api.UKeyCertificateBinding, 'objects'),
            'commit': patch.object(api.transaction, 'on_commit'),
        }
        for name, mock in patches.items():
            setattr(self, name, mock.start())
            self.addCleanup(mock.stop)
        self.users.filter.return_value.select_for_update.return_value.get.return_value = self.user
        self.bindings.filter.return_value.first.return_value = None

    def test_verified_vctks_certificate_replaces_existing_binding_for_same_user(self):
        # update_or_create keys only by user, allowing an existing XJCA row to be replaced.
        response = self.view.post(self.request)
        self.assertEqual(response.status_code, 200)
        self.consume.assert_called_once_with(self.request, 'c' * 43, 'bind', self.user.pk)
        self.verify.assert_called_once_with(self.state, 'ab' * 32, 'certificate', 'p' * 5000)
        call = self.bindings.update_or_create.call_args.kwargs
        self.assertEqual(call['user'], self.user)
        self.assertEqual(call['defaults']['provider'], 'vctk_s')
        self.assertEqual(call['defaults']['certificate_fingerprint'], 'b' * 64)
        self.assertEqual(call['defaults']['hardware_serial'], 'device-serial')
        self.assertTrue(call['defaults']['version'])
        self.view.check_object_permissions.assert_called_once_with(self.request, self.user)

    def test_xjca_can_replace_vctks_binding_using_original_limit_and_interface(self):
        self.state.update(AUTH_UKEY_CA_PROVIDER='xjca', AUTH_UKEY_VENDOR='long_mai')
        self.identity['provider'] = 'xjca'
        self.payload['signature'] = 'raw-signature'
        self.view.post(self.request)
        self.assertEqual(self.bindings.update_or_create.call_args.kwargs['defaults']['provider'], 'xjca')
        self.assertEqual(self.bindings.update_or_create.call_args.kwargs['user'], self.user)

    def test_bad_signature_or_changed_binding_preserves_previous_binding(self):
        self.verify.side_effect = UKeyAuthError('Rejected proof')
        with self.assertRaises(ValidationError):
            self.view.post(self.request)
        self.bindings.update_or_create.assert_not_called()
        self.bindings.filter.return_value.delete.assert_not_called()
        self.verify.side_effect = None
        self.version.return_value = 'new-binding-version'
        with self.assertRaises(ValidationError):
            self.view.post(self.request)
        self.bindings.update_or_create.assert_not_called()

    def test_revoked_object_permission_preserves_previous_binding(self):
        self.view.check_object_permissions.side_effect = PermissionDenied()
        with self.assertRaises(PermissionDenied):
            self.view.post(self.request)
        self.bindings.update_or_create.assert_not_called()

    def test_unbind_only_removes_current_provider_binding_with_expected_version(self):
        self.payload.update(action='unbind', binding_version='version-1')
        self.version.return_value = 'version-1'
        self.view.post(self.request)
        self.bindings.filter.assert_any_call(user=self.user, provider='vctk_s')
        self.bindings.filter.return_value.delete.assert_called_once()
        self.verify.assert_not_called()
        self.consume.assert_not_called()

    def test_attached_signature_size_increases_only_for_vctks(self):
        for cls, length in (
            (api.VCTKSBindingSerializer, 43692),
            (api.UKeyCertificateBindingSerializer, 4096),
        ):
            self.payload['signature'] = 'p' * length
            self.assertTrue(cls(data=self.payload).is_valid())
            self.payload['signature'] += 'p'
            self.assertFalse(cls(data=self.payload).is_valid())
        self.assertEqual(CertificateUKeyLoginForm.base_fields['signature'].max_length, 4096)
        self.assertEqual(VCTKSCertificateLoginForm.base_fields['signature'].max_length, 43692)
        self.assertFalse(VCTKSCertificateLoginForm.base_fields['username'].required)

    def test_management_permissions_are_unchanged(self):
        self.assertEqual(self.view.rbac_perms['POST'], 'users.change_user')
        self.assertEqual(self.view.rbac_perms['GET'], 'users.change_user')
        self.assertIn(api.UserObjectPermission, self.view.permission_classes)

    def test_login_form_selection_preserves_other_modes(self):
        for vendor, provider, expected in (
            ('ji_da', 'builtin', UKeyLoginForm), ('long_mai', 'builtin', UKeyLoginForm),
            ('long_mai', 'xjca', CertificateUKeyLoginForm), ('ji_da', 'vctk_s', VCTKSCertificateLoginForm),
        ):
            view = UKeyLoginView()
            view.provider = get_provider(snapshot(AUTH_UKEY_VENDOR=vendor, AUTH_UKEY_CA_PROVIDER=provider))
            self.assertIs(view.get_form_class(), expected)

    def test_sdk_only_exposes_current_authenticated_users_binding(self):
        request = SimpleNamespace(
            query_params={}, COOKIES={},
            user=SimpleNamespace(pk='self-user', is_authenticated=True, has_perm=lambda perm: False),
        )
        with patch.object(api.UKeySDKConfig, 'get_sdk_config', side_effect=lambda **kwargs: {'config': {}}), \
                patch.object(api.UKeyCertificateBindingAPI, 'binding_data', return_value={'bound': True}) as read:
            result = api.UKeySDKConfigFileAPIView().get(request).data
            read.assert_called_once_with('self-user', 'vctk_s')
            self.assertEqual(result['config']['own_binding'], {'user_id': 'self-user', 'bound': True})
            request.user.is_authenticated = False
            read.reset_mock()
            self.assertNotIn('own_binding', api.UKeySDKConfigFileAPIView().get(request).data['config'])
            read.assert_not_called()


class VCTKSPendingLoginTests(SimpleTestCase):
    def test_rebinding_or_unbinding_invalidates_pending_login(self):
        user = SimpleNamespace(pk='user-id')
        for version in ('', 'replacement-version'):
            request = SimpleNamespace(
                user=SimpleNamespace(is_authenticated=False),
                session={'auth_ukey_state': {
                    'provider': 'vctk_s', 'user_id': 'user-id',
                    'revision': snapshot()[REVISION], 'expires': time.time() + 300,
                    'binding_version': 'original-version',
                }, 'auth_ukey': True},
            )
            with patch.object(pending, 'binding_version', return_value=version):
                with self.assertRaises(SessionEmptyError):
                    pending.validate_pending_user(request, user, snapshot())
            self.assertNotIn('auth_ukey_state', request.session)
            self.assertNotIn('auth_ukey', request.session)
