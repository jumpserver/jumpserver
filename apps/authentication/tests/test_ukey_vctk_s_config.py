"""VCTK_S certificate binding must preserve the other providers and JIT PIN operations."""
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import ValidationError

from authentication.backends.ukey.configuration import REVISION, SECRET_FIELDS
from authentication.backends.ukey.exceptions import UKeyAuthError
from authentication.backends.ukey.providers import get_provider
from authentication.backends.ukey.sdk import UKeySDKConfig
from settings.serializers.auth.ukey import UKeySettingSerializer, UKeyTestingSerializer


ROOT = Path(__file__).resolve().parents[3]


def snapshot(**overrides):
    return {
        'AUTH_UKEY': True,
        'AUTH_UKEY_VENDOR': 'ji_da',
        'AUTH_UKEY_CA_PROVIDER': 'vctk_s',
        REVISION: 'test-revision',
        'AUTH_UKEY_CHALLENGE_TTL': 300,
        'AUTH_UKEY_ENROLL_ENABLED': True,
        'AUTH_UKEY_ENROLL_VALIDITY_DAYS': 365,
        'AUTH_UKEY_DEFAULT_PIN': '123456',
        'AUTH_UKEY_CA_CERT_CONTENT': '',
        'AUTH_UKEY_VCTK_S_SVS_URL': 'http://192.0.2.1:8000',
        'AUTH_UKEY_VCTK_S_ISSUING_CA': 'saved-issuing-ca',
        'AUTH_UKEY_VCTK_S_TLS_VERIFY': 'system',
        'AUTH_UKEY_VCTK_S_TLS_CA_CERT': 'saved-https-ca',
        'AUTH_UKEY_VCTK_S_USERNAME': 'business-user',
        'AUTH_UKEY_VCTK_S_PASSWORD': 'saved-password',
        **overrides,
    }


@override_settings(PROJECT_DIR=str(ROOT), DEBUG_DEV=False)
class SDKCompatibilityTests(SimpleTestCase):
    def setUp(self):
        self.reverse = patch(
            'authentication.backends.ukey.sdk.reverse',
            side_effect=lambda name: '/api/' + name.rsplit(':', 1)[-1] + '/',
        )
        self.reverse.start()
        self.addCleanup(self.reverse.stop)

    def test_reuses_original_jida_script_detection_pin_and_submit(self):
        builtin = UKeySDKConfig(snapshot(AUTH_UKEY_CA_PROVIDER='builtin'))
        remote = UKeySDKConfig(snapshot())
        self.assertTrue(remote.load_sdk_script_content().startswith(builtin.load_sdk_script_content()))
        self.assertIn(b'VCTKSCertificateDigest', remote.load_sdk_script_content())
        self.assertNotIn(b'VCTKSCertificateDigest', builtin.load_sdk_script_content())
        builtin_config = builtin.get_sdk_config(include_admin_pin=True)
        remote_config = remote.get_sdk_config(include_admin_pin=True)
        self.assertEqual(builtin_config['sdk'], remote_config['sdk'])
        operations = {item['key']: item for item in remote_config['operations']['items']}
        builtin_operations = {item['key']: item for item in builtin_config['operations']['items']}
        self.assertEqual(set(operations), {'bindUserUKeySN', 'unbindUserUKeySN', 'resetPin', 'changePIN'})
        for key in ('resetPin', 'changePIN'):
            self.assertEqual(operations[key], builtin_operations[key])
        login = remote_config['login']
        self.assertEqual([s['name'] for s in login['steps']], ['verifyPin', 'getCert', 'signChallenge', 'submit'])
        self.assertEqual(login['steps'][-1]['fields']['username'], '')
        self.assertEqual(login['steps'][-1]['fields']['ukey_sn'], '{{ ukey.devSN }}')
        self.assertNotIn('compare', remote_config['info']['cert'][0])
        self.assertEqual(builtin_config['info']['cert'][0]['compare'], '{{ user.username }}')
        self.assertNotIn('user_detail_url', remote_config['config']['api'])
        self.assertNotIn('UKey_DeleteCons', repr(remote_config['operations']))
        self.assertNotIn('UKey_GenKey', repr(remote_config['operations']))
        self.assertEqual(remote_config['config']['pin'], builtin_config['config']['pin'])
        self.assertFalse(remote_config['config']['enroll']['enabled'])
        self.assertTrue(builtin_config['config']['enroll']['enabled'])
        self.assertTrue(remote_config['config']['capabilities']['uses_one_time_challenge'])
        self.assertFalse(builtin_config['config']['capabilities']['uses_one_time_challenge'])
        self.assertNotIn('saved-password', repr(remote_config))
        self.assertNotIn('business-user', repr(remote_config))

    def test_provider_override_does_not_mutate_cached_builtin_config(self):
        remote = UKeySDKConfig(snapshot())
        remote.get_sdk_config()
        builtin = UKeySDKConfig(snapshot(AUTH_UKEY_CA_PROVIDER='builtin'))
        sign = next(step for step in builtin.get_sdk_config()['login']['steps']
                    if step['name'] == 'signChallenge')
        self.assertEqual(sign['call'], 'UKey_SignData')

    def test_binding_proves_possession_before_saving_and_unbind_never_calls_device(self):
        config = UKeySDKConfig(snapshot()).get_sdk_config()
        operations = {item['key']: item for item in config['operations']['items']}
        bind = operations['bindUserUKeySN']['steps']
        self.assertEqual([step.get('call') or step['body']['action'] for step in bind], [
            'UKey_VerifyPIN', 'UKey_GetCert', 'challenge', 'UKey_P7SignAttach', 'bind',
        ])
        self.assertEqual(bind[3]['digest_certificate'], '{{ ukey.cert }}')
        self.assertEqual(bind[3]['args'][1], '{{ vars.challenge.code_base64 }}')
        self.assertEqual(bind[-1]['body']['hardware_serial'], '{{ ukey.devSN }}')
        self.assertEqual(bind[-1]['url_format'], {'user_id': '{{ user.id }}'})
        unbind = operations['unbindUserUKeySN']
        self.assertFalse(unbind['requires_device'])
        self.assertEqual(len(unbind['steps']), 1)
        self.assertEqual(unbind['steps'][0]['type'], 'api')
        self.assertEqual(unbind['steps'][0]['body']['binding_version'], '{{ ukey.binding.binding_version }}')
        self.assertIn('ukey.binding.hardware_serial', config['operations']['when'])
        self.assertNotIn('user.ukey_sn', config['operations']['when'])

    def test_default_pin_is_admin_only(self):
        config = UKeySDKConfig(snapshot())
        self.assertNotIn('pin', config.get_sdk_config()['config'])
        self.assertEqual(config.get_sdk_config(include_admin_pin=True)['config']['pin']['default'], '123456')

    def test_ca_algorithm_never_selects_login_signing_digest(self):
        for algorithm in ('RSA', 'SM2', 'RSA / SM2', ''):
            with self.subTest(algorithm=algorithm), patch(
                'authentication.backends.ukey.providers.vctk_s.VCTKSCAProvider.ca_algorithm',
                new=property(lambda self: algorithm),
            ):
                config = UKeySDKConfig(snapshot()).get_sdk_config()
                sign = next(step for step in config['login']['steps'] if step['name'] == 'signChallenge')
                self.assertEqual(config['config']['asym_alg_name'], algorithm)
                self.assertEqual(sign['digest_certificate'], '{{ ukey.cert }}')

    def test_certificate_identity_does_not_require_longmai_container_selection(self):
        provider = get_provider(snapshot())
        self.assertEqual(provider.binding_mode, 'certificate')
        self.assertFalse(provider.requires_certificate_selection)
        self.assertFalse(provider.supports_enrollment)
        self.assertTrue(provider.expose_default_pin)
        with self.assertRaises(UKeyAuthError):
            get_provider(snapshot(AUTH_UKEY_VENDOR='long_mai'))

    def test_longmai_provider_and_sdk_profile_still_work(self):
        config = UKeySDKConfig(snapshot(AUTH_UKEY_VENDOR='long_mai', AUTH_UKEY_CA_PROVIDER='xjca'))
        result = config.get_sdk_config()
        self.assertEqual(result['config']['capabilities']['binding_mode'], 'certificate')
        self.assertEqual(config.provider.sdk_profile, 'sdk_config_xjca.yaml')
        constructor = result['sdk']['create']['constructor'].encode()
        self.assertTrue(b'function ' + constructor in config.load_sdk_script_content())
        self.assertNotIn('UKey_P7SignDetach', repr(result['login']))


class SettingsTests(SimpleTestCase):
    def test_ca_parse_error_is_reported_on_the_ca_upload_field(self):
        serializer = UKeySettingSerializer(data={
            'AUTH_UKEY_VCTK_S_ISSUING_CA': 'not a certificate',
        }, context={'snapshot': snapshot()}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('AUTH_UKEY_VCTK_S_ISSUING_CA', serializer.errors)

    def test_public_settings_expose_status_but_not_uploaded_certificates(self):
        result = UKeySettingSerializer(instance=snapshot()).data
        self.assertTrue(result['AUTH_UKEY_VCTK_S_ISSUING_CA_CONFIGURED'])
        for key in ('AUTH_UKEY_VCTK_S_ISSUING_CA', 'AUTH_UKEY_VCTK_S_TLS_CA_CERT',
                    'AUTH_UKEY_VCTK_S_PASSWORD'):
            self.assertNotIn(key, result)
            self.assertIn(key, SECRET_FIELDS)
        provider = next(p for p in result['AUTH_UKEY_CA_PROVIDERS'] if p['id'] == 'vctk_s')
        self.assertEqual(provider['supported_vendors'], ['ji_da'])
        self.assertEqual(provider['binding_mode'], 'certificate')
        self.assertEqual(set(provider['fields']), {
            'AUTH_UKEY_VCTK_S_SVS_URL', 'AUTH_UKEY_VCTK_S_TLS_VERIFY',
            'AUTH_UKEY_VCTK_S_TLS_CA_CERT', 'AUTH_UKEY_VCTK_S_ISSUING_CA',
            'AUTH_UKEY_VCTK_S_USERNAME', 'AUTH_UKEY_VCTK_S_PASSWORD',
        })
        self.assertEqual(set(provider['connection_fields']), set(provider['fields']) - {
            'AUTH_UKEY_VCTK_S_ISSUING_CA',
        })

    def test_blank_password_keeps_saved_secret_and_empty_username_disables_authorization(self):
        with patch('authentication.backends.ukey.providers.vctk_s.VCTKSVerifier') as verifier:
            serializer = UKeySettingSerializer(
                data={'AUTH_UKEY_VCTK_S_USERNAME': '', 'AUTH_UKEY_VCTK_S_PASSWORD': ''},
                partial=True, context={'snapshot': snapshot()},
            )
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(verifier.call_args.kwargs['username'], '')
            self.assertEqual(verifier.call_args.kwargs['password'], 'saved-password')
        serializer = UKeyTestingSerializer(
            data={'AUTH_UKEY_CA_PROVIDER': 'vctk_s', 'AUTH_UKEY_VCTK_S_PASSWORD': ''},
            context={'snapshot': snapshot()},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('AUTH_UKEY_VCTK_S_PASSWORD', serializer.validated_data)

    def test_blank_upload_keeps_saved_ca_during_validation(self):
        state = snapshot()
        with patch('authentication.backends.ukey.providers.vctk_s.VCTKSVerifier') as verifier:
            serializer = UKeySettingSerializer(
                data={'AUTH_UKEY_VCTK_S_ISSUING_CA': '', 'AUTH_UKEY_VCTK_S_TLS_CA_CERT': ''},
                partial=True, context={'snapshot': state},
            )
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(verifier.call_args.kwargs['issuing_ca'], 'saved-issuing-ca')
            self.assertEqual(verifier.call_args.kwargs['tls_ca_cert'], 'saved-https-ca')

    def test_missing_required_settings_and_incompatible_vendor(self):
        for missing in ('AUTH_UKEY_VCTK_S_SVS_URL', 'AUTH_UKEY_VCTK_S_ISSUING_CA'):
            with self.subTest(missing=missing), self.assertRaises(ValidationError) as error:
                get_provider(snapshot(**{missing: ''})).validate_config()
            self.assertIn(missing, error.exception.detail)
        serializer = UKeySettingSerializer(
            data={'AUTH_UKEY_VENDOR': 'long_mai'}, partial=True, context={'snapshot': snapshot()},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('AUTH_UKEY_VENDOR', serializer.errors)

    def test_custom_https_requires_ca_but_http_and_system_do_not(self):
        with self.assertRaises(ValidationError) as error:
            get_provider(snapshot(
                AUTH_UKEY_VCTK_S_SVS_URL='https://192.0.2.1',
                AUTH_UKEY_VCTK_S_TLS_VERIFY='custom', AUTH_UKEY_VCTK_S_TLS_CA_CERT='',
            )).validate_config()
        self.assertIn('AUTH_UKEY_VCTK_S_TLS_CA_CERT', error.exception.detail)
        with patch('authentication.backends.ukey.providers.vctk_s.VCTKSVerifier'):
            for url, trust in (('http://192.0.2.1', 'custom'), ('https://192.0.2.1', 'system')):
                get_provider(snapshot(
                    AUTH_UKEY_VCTK_S_SVS_URL=url, AUTH_UKEY_VCTK_S_TLS_VERIFY=trust,
                    AUTH_UKEY_VCTK_S_TLS_CA_CERT='',
                )).validate_config()

    def test_disabling_remains_possible_with_unusable_service_and_ca(self):
        get_provider(snapshot(
            AUTH_UKEY=False, AUTH_UKEY_VCTK_S_SVS_URL='', AUTH_UKEY_VCTK_S_ISSUING_CA='',
        )).validate_config()

    def test_connection_test_only_accepts_service_settings(self):
        context = {'snapshot': snapshot()}
        serializer = UKeyTestingSerializer(data={
            'AUTH_UKEY_VENDOR': 'ji_da', 'AUTH_UKEY_CA_PROVIDER': 'vctk_s',
            'AUTH_UKEY_VCTK_S_TLS_CA_CERT': '',
        }, context=context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('AUTH_UKEY_VCTK_S_TLS_CA_CERT', serializer.validated_data)
        serializer = UKeyTestingSerializer(data={
            'AUTH_UKEY_CA_PROVIDER': 'vctk_s', 'AUTH_UKEY_VCTK_S_ISSUING_CA': 'not-a-connection-field',
        }, context=context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('AUTH_UKEY_VCTK_S_ISSUING_CA', serializer.errors)
