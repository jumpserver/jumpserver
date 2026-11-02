"""Session-bound, single-use challenges for JiDa VCTK_S certificate identity."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from authentication.backends.ukey import challenges
from authentication.backends.ukey.configuration import REVISION
from authentication.backends.ukey.exceptions import UKeyAuthError, UKeyServiceError
from authentication.backends.ukey.forms import VCTKSCertificateLoginForm
from authentication.backends.ukey.providers import get_provider
from authentication.tests.test_ukey_vctk_s_config import snapshot


def request(session='browser-session'):
    return SimpleNamespace(
        session=SimpleNamespace(session_key=session),
        user=SimpleNamespace(is_authenticated=False),
        META={'REMOTE_ADDR': '192.0.2.2'},
    )


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class VCTKSChallengeTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.snapshot = snapshot()
        self.provider = get_provider(self.snapshot)
        self.request = request()
        mocked = patch.object(challenges, 'get_snapshot', side_effect=lambda: self.snapshot)
        mocked.start()
        self.addCleanup(mocked.stop)
        generated = patch(
            'authentication.backends.ukey.providers.vctk_s.VCTKSVerifier.generate_challenge',
            return_value='ab' * 32,
        )
        self.generate = generated.start()
        self.addCleanup(generated.stop)

    def test_certificate_provider_issues_remote_challenge_and_consumes_once(self):
        issued = challenges.issue(self.request, 'login')
        self.generate.assert_called_once_with()
        self.assertEqual(issued['code'], 'ab' * 32)
        self.assertEqual(issued['length'], 64)
        self.assertEqual(self.provider.binding_mode, 'certificate')
        record, state = challenges.consume(self.request, issued['id'], 'login')
        self.assertEqual(record['code'], issued['code'])
        self.assertEqual(state[REVISION], issued['revision'])
        with self.assertRaises(UKeyAuthError):
            challenges.consume(self.request, issued['id'], 'login')
        self.assertTrue(cache.get('ukey:consumed:' + issued['id']))

    def test_expiration_session_purpose_actor_and_revision_are_checked(self):
        for changed in ('expires', 'session', 'purpose', 'actor', 'revision', 'provider'):
            with self.subTest(changed=changed):
                issued = challenges.issue(self.request, 'login')
                key = 'ukey:challenge:' + issued['id']
                record = cache.get(key)
                record[changed] = 0 if changed == 'expires' else 'different'
                cache.set(key, record, 300)
                with self.assertRaises(UKeyAuthError):
                    challenges.consume(self.request, issued['id'], 'login')
                self.assertIsNone(cache.get('ukey:consumed:' + issued['id']))

    def test_two_concurrent_submissions_only_one_can_claim(self):
        issued = challenges.issue(self.request, 'login')
        token = issued['id']
        barrier = Barrier(2)
        original_get = cache.get

        def overlapping_get(key, *args, **kwargs):
            value = original_get(key, *args, **kwargs)
            if key == 'ukey:challenge:' + token:
                barrier.wait(timeout=5)
            return value

        def claim():
            try:
                challenges.consume(self.request, token, 'login')
                return True
            except UKeyAuthError:
                return False

        with patch.object(cache, 'get', side_effect=overlapping_get):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: claim(), range(2)))
        self.assertEqual(sorted(results), [False, True])

    def test_failed_random_request_never_issues_a_local_fallback(self):
        self.generate.side_effect = UKeyServiceError('Service unavailable')
        with self.assertRaises(UKeyServiceError), patch.object(cache, 'set') as store:
            challenges.issue(self.request, 'login')
        self.assertFalse(any(call.args[0].startswith('ukey:challenge:') for call in store.call_args_list))

    def test_settings_change_while_generating_invalidates_new_challenge(self):
        def generate():
            self.snapshot = snapshot(**{REVISION: 'new-revision'})
            return 'ab' * 32

        self.generate.side_effect = generate
        with self.assertRaises(UKeyAuthError):
            challenges.issue(self.request, 'login')

    def test_builtin_keeps_its_existing_challenge_flow(self):
        self.snapshot = snapshot(AUTH_UKEY_CA_PROVIDER='builtin')
        self.assertFalse(get_provider(self.snapshot).uses_one_time_challenge)
        with self.assertRaises(UKeyAuthError):
            challenges.issue(self.request, 'login')
        self.generate.assert_not_called()

    def test_login_form_requires_id_and_accepts_bounded_attached_p7(self):
        data = {'username': '', 'cert': 'cert', 'signature': 'a' * 43692, 'ukey_sn': 'serial'}
        self.assertFalse(VCTKSCertificateLoginForm(data=data).is_valid())
        data['challenge_id'] = 'a' * 43
        self.assertTrue(VCTKSCertificateLoginForm(data=data).is_valid())
        data['signature'] += 'a'
        self.assertFalse(VCTKSCertificateLoginForm(data=data).is_valid())
