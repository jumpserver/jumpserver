from common.utils import gen_key_pair, reverse, rsa_decrypt, rsa_encrypt
from django.test import RequestFactory, SimpleTestCase, override_settings

from authentication.api.sso import SSOViewSet
from users.views.profile.password import UserVerifyPasswordView


def test_rsa_encrypt_decrypt(message='test-password-$%^&*'):
    """ 测试加密/解密 """
    print('Need to encrypt message: {}'.format(message))
    rsa_private_key, rsa_public_key = gen_key_pair()
    print('RSA public key: \n{}'.format(rsa_public_key))
    print('RSA private key: \n{}'.format(rsa_private_key))
    message_encrypted = rsa_encrypt(message, rsa_public_key)
    print('Encrypted message: {}'.format(message_encrypted))
    message_decrypted = rsa_decrypt(message_encrypted, rsa_private_key)
    print('Decrypted message: {}'.format(message_decrypted))


class SSOLoginRedirectTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(ALLOWED_HOSTS=['testserver'])
    def test_scheme_relative_next_url_is_rejected(self):
        request = self.factory.get(
            '/api/v1/authentication/sso/login/',
            {'next': '//attacker.example.com'}
        )

        self.assertEqual(SSOViewSet.get_safe_next_url(request), reverse('index'))

    @override_settings(ALLOWED_HOSTS=['testserver'])
    def test_local_next_url_is_preserved(self):
        request = self.factory.get('/api/v1/authentication/sso/login/', {'next': '/ui/#/workbench'})

        self.assertEqual(SSOViewSet.get_safe_next_url(request), '/ui/#/workbench')


class UserVerifyPasswordRedirectTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(ALLOWED_HOSTS=['testserver'])
    def test_scheme_relative_next_url_is_rejected(self):
        request = self.factory.get(
            '/core/auth/password/verify/',
            {'next': '//attacker.example.com'}
        )
        view = UserVerifyPasswordView()
        view.request = request

        self.assertEqual(view.get_success_url(), '/')

    @override_settings(ALLOWED_HOSTS=['testserver'])
    def test_local_next_url_is_preserved(self):
        request = self.factory.get('/core/auth/password/verify/', {'next': '/ui/#/profile/index'})
        view = UserVerifyPasswordView()
        view.request = request

        self.assertEqual(view.get_success_url(), '/ui/#/profile/index')
