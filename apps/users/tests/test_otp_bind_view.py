from unittest.mock import MagicMock

from django.test import SimpleTestCase

from users.views.profile.otp import UserOtpEnableBindView


class OtpBindViewSecretReuseTest(SimpleTestCase):
    """The bind page must keep one secret per binding flow.

    Regression test: get_context_data() used to generate a new secret on
    every render and overwrite the session value, so after a single invalid
    code (form_invalid re-render) or a page refresh, the QR code/secret shown
    no longer matched the one already enrolled in the user's authenticator
    app, and verification could never succeed afterwards.
    """

    def _make_view(self, session):
        view = UserOtpEnableBindView()
        request = MagicMock()
        request.session = session
        view.request = request
        view.kwargs = {}
        return view

    def test_secret_is_reused_across_renders(self):
        session = {}
        view = self._make_view(session)

        first = view.get_context_data()
        secret_after_first_render = session['otp_secret_key']

        # Simulate form_invalid()/refresh: context is built again
        second = view.get_context_data()

        self.assertEqual(
            session['otp_secret_key'], secret_after_first_render,
            'secret must not rotate within one binding flow',
        )
        self.assertEqual(
            second['otp_secret_key'], secret_after_first_render)
        # The QR URI must be rebuilt from the same secret, otherwise the
        # rendered QR code would still encode a different key
        self.assertIn(secret_after_first_render.split('=')[0][:6],
                      second['otp_uri'])

    def test_first_render_generates_and_stores_secret(self):
        session = {}
        view = self._make_view(session)
        ctx = view.get_context_data()
        self.assertIn('otp_secret_key', session)
        self.assertEqual(ctx['otp_secret_key'], session['otp_secret_key'])
