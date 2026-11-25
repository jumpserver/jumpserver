import json
import time
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from pyrad.client import Timeout
from pyrad.packet import AccessAccept, AccessChallenge, AccessReject

from authentication.backends.radius import RadiusBackend
from authentication.const import MFAType
from authentication.mfa.radius import MFARadius
from authentication.services.radius_push import RadiusPushAttempt, SEND_INTERVAL
from authentication.views.mfa import UserLoginRadiusPushView


class LoginSession(dict):
    session_key = 'radius-push-test-session'


@override_settings(
    AUTH_RADIUS=True,
    OTP_IN_RADIUS=True,
    RADIUS_MFA_MODE='push',
    RADIUS_PUSH_TIMEOUT=75,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class RadiusPushTest(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = SimpleNamespace(
            pk='user-1', username='test-user', is_valid=True, mfa_enabled=True,
            get_active_mfa_backend_by_type=Mock(return_value=object()),
        )
        self.session = LoginSession(
            auth_password=1, auth_password_expired_at=time.time() + 120, user_id=self.user.pk,
        )
        self.attempt = RadiusPushAttempt.for_session(self.session, self.user)
        self.factory = RequestFactory()
        lock = patch('authentication.services.radius_push.DistributedLock', return_value=nullcontext())
        lock.start()
        self.addCleanup(lock.stop)
        model = patch('authentication.services.radius_push.get_user_model')
        model.start().return_value.objects.filter.return_value.first.return_value = self.user
        self.addCleanup(model.stop)
        blocks = patch('authentication.services.radius_push.MFABlockUtils')
        self.blocks = blocks.start().return_value
        self.blocks.is_block.return_value = False
        self.addCleanup(blocks.stop)

    def start(self):
        attempt, created = self.attempt.start(self.user, '127.0.0.1', self.session['auth_password_expired_at'])
        self.assertTrue(created)
        return attempt['id']

    def request(self, action, attempt='', *, csrf=True):
        request = self.factory.post('/core/auth/login/mfa/radius-push/', {'action': action, 'attempt': attempt})
        request.session = self.session
        request._dont_enforce_csrf_checks = not csrf
        with patch.object(UserLoginRadiusPushView, 'get_user_from_session', return_value=self.user), \
                patch.object(UserLoginRadiusPushView, 'check_mfa_is_block'):
            return UserLoginRadiusPushView.as_view()(request)

    @patch.object(RadiusBackend, 'authenticate_push', return_value='rejected')
    def test_duplicates_send_and_count_one_rejection(self, authenticate):
        attempt_id = self.start()
        existing, created = self.attempt.start(
            self.user, '127.0.0.1', self.session['auth_password_expired_at'],
        )
        self.assertFalse(created)
        self.assertEqual(existing['id'], attempt_id)
        self.attempt.run(attempt_id)
        self.attempt.run(attempt_id)
        authenticate.assert_called_once()
        self.blocks.incr_failed_count.assert_called_once_with()
        self.assertEqual(self.attempt.get(attempt_id)['status'], 'rejected')
        self.assertTrue(cache.get(f'radius-push-send:{self.user.pk}'))

    @patch.object(RadiusBackend, 'authenticate_push')
    def test_cancel_discards_approval_and_keeps_cooldown(self, authenticate):
        attempt_id = self.start()

        def finish_after_cancel(username, timeout):
            self.attempt.cancel(attempt_id)
            return 'approved'

        authenticate.side_effect = finish_after_cancel
        self.attempt.run(attempt_id)
        self.assertEqual(self.attempt.get(attempt_id)['status'], 'cancelled')
        self.assertIsNone(self.attempt.transition(attempt_id, {'approved'}, 'consumed'))
        self.assertEqual(
            self.attempt.start(self.user, '127.0.0.1', self.session['auth_password_expired_at']),
            (None, False),
        )
        self.blocks.incr_failed_count.assert_not_called()

    @patch.object(RadiusBackend, 'authenticate_push', return_value='timed_out')
    def test_timeout_does_not_count_as_failed_mfa(self, authenticate):
        attempt_id = self.start()
        self.attempt.run(attempt_id)
        self.assertEqual(self.attempt.get(attempt_id)['status'], 'timed_out')
        self.blocks.incr_failed_count.assert_not_called()

    def test_attempt_is_bound_to_session_and_primary_authentication(self):
        attempt_id = self.start()
        other = LoginSession(self.session)
        other.session_key = 'another-test-session'
        self.assertIsNone(RadiusPushAttempt.for_session(other, self.user).get(attempt_id))
        self.session['auth_password_expired_at'] += SEND_INTERVAL
        self.assertIsNone(RadiusPushAttempt.for_session(self.session, self.user).get(attempt_id))
        self.session['auth_password_expired_at'] = time.time() - 1
        self.assertIsNone(RadiusPushAttempt.for_session(self.session, self.user))

    @override_settings(CSRF_FAILURE_VIEW='django.views.csrf.csrf_failure')
    def test_start_requires_csrf_and_live_primary_authentication(self):
        self.assertEqual(self.request('start').status_code, 403)
        self.session.pop('auth_password')
        self.assertEqual(self.request('start', csrf=False).status_code, 403)
        self.assertIsNone(self.attempt.get())

    @patch('authentication.tasks.authenticate_radius_push.apply_async')
    def test_start_enqueues_once_and_completion_requires_approval(self, enqueue):
        result = json.loads(self.request('start', csrf=False).content)
        attempt_id = result['attempt']
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(json.loads(self.request('start', csrf=False).content), result)
        enqueue.assert_called_once_with(args=(self.attempt.key, attempt_id), expires=75, retry=False)

        response = self.request('complete', attempt_id, csrf=False)
        self.assertEqual(json.loads(response.content)['status'], 'pending')
        self.assertNotIn('auth_mfa', self.session)
        self.attempt.transition(attempt_id, {'queued'}, 'approved')

        with patch('authentication.mixins.MFABlockUtils'):
            response = self.request('complete', attempt_id, csrf=False)
        self.assertEqual(json.loads(response.content)['status'], 'complete')
        self.assertEqual(self.session['auth_mfa_type'], MFAType.Radius.value)
        self.assertEqual(self.attempt.get(attempt_id)['status'], 'consumed')

    def test_login_form_displays_push_controls_only_in_push_mode(self):
        context = {'mfa_backends': [MFARadius(self.user)], 'radius_push_controls': True}
        code = render_to_string('_mfa_login_field.html', context)
        push = render_to_string('_mfa_login_field.html', {**context, 'radius_push_enabled': True})
        self.assertIn('class="form-control input-style"', code)
        self.assertNotIn('id="radius-push"', code)
        self.assertNotIn('class="form-control input-style"', push)
        self.assertIn(f'data-type="{MFAType.Radius.value}"', push)


@override_settings(RADIUS_SERVER='localhost', RADIUS_PORT=1812, RADIUS_SECRET='test secret', RADIUS_ATTRIBUTES={})
class RadiusPushTransportTest(SimpleTestCase):
    @patch('pyrad.client.Client.SendPacket')
    def test_sends_one_rfc_compliant_empty_pap_password(self, send):
        send.return_value.code = AccessAccept
        self.assertEqual(RadiusBackend().authenticate_push('test-user', 70), 'approved')
        packet = send.call_args.args[0]
        self.assertEqual(packet['User-Name'], ['test-user'])
        password = packet[2][0]
        self.assertEqual(len(password), 16)
        self.assertEqual(packet.PwDecrypt(password), '')
        send.assert_called_once()

    @patch('pyrad.client.Client.SendPacket', autospec=True)
    def test_distinguishes_rejection_challenge_and_timeout(self, send):
        backend = RadiusBackend()
        for reply, result in [(AccessReject, 'rejected'), (AccessChallenge, 'failed')]:
            with self.subTest(reply=reply):
                send.return_value.code = reply
                self.assertEqual(backend.authenticate_push('test-user', 70), result)
                client = send.call_args.args[0]
                self.assertEqual((client.retries, client.timeout), (1, 70))
        send.side_effect = Timeout
        self.assertEqual(backend.authenticate_push('test-user', 70), 'timed_out')
