from django.conf import settings
from onelogin.saml2.settings import OneLogin_Saml2_Settings


class JmsSaml2Settings(OneLogin_Saml2_Settings):
    def get_sp_key(self):
        key = getattr(settings, 'SAML2_SP_KEY_CONTENT', '')
        return key

    def get_sp_cert(self):
        cert = getattr(settings, 'SAML2_SP_CERT_CONTENT', '')
        return cert
