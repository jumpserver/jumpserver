import os

import ldap
from django.conf import settings
from django.utils._os import safe_join

from jumpserver.const import CONFIG, PROJECT_DIR

__all__ = ['LDAPTLSUtil']


class LDAPTLSUtil:
    @staticmethod
    def tls_supports_cert_files():
        """SecureTransport (macOS) does not support TLS cert file ldap options."""
        try:
            return ldap.get_option(ldap.OPT_X_TLS_PACKAGE) != 'SecureTransport'
        except ldap.LDAPError:
            return True

    FILE_MAP = {
        'ldap': {
            'ca': ('AUTH_LDAP_CACERT_CONTENT', 'ldap_ca.pem', ldap.OPT_X_TLS_CACERTFILE),
            'cert': ('AUTH_LDAP_CERT_CONTENT', 'ldap_cert.pem', ldap.OPT_X_TLS_CERTFILE),
            'key': ('AUTH_LDAP_KEY_CONTENT', 'ldap_cert.key', ldap.OPT_X_TLS_KEYFILE),
        },
        'ldap_ha': {
            'ca': ('AUTH_LDAP_HA_CACERT_CONTENT', 'ldap_ha_ca.pem', ldap.OPT_X_TLS_CACERTFILE),
            'cert': ('AUTH_LDAP_HA_CERT_CONTENT', 'ldap_ha_cert.pem', ldap.OPT_X_TLS_CERTFILE),
            'key': ('AUTH_LDAP_HA_KEY_CONTENT', 'ldap_ha_cert.key', ldap.OPT_X_TLS_KEYFILE),
        },
    }

    def __init__(self, category):
        self.category = category

    @property
    def prefix(self):
        return f'AUTH_{self.category.upper()}'

    def get_cert_dir(self):
        return safe_join(PROJECT_DIR, 'data', 'certs')

    def get_cert_file_path(self, filename):
        return safe_join(self.get_cert_dir(), filename)

    def write_cert_file(self, filename, content):
        cert_dir = self.get_cert_dir()
        os.makedirs(cert_dir, mode=0o700, exist_ok=True)
        filepath = self.get_cert_file_path(filename)
        with open(filepath, 'w') as f:
            f.write(content)
        os.chmod(filepath, 0o600)
        return filepath

    def remove_cert_file(self, filename):
        filepath = self.get_cert_file_path(filename)
        if os.path.isfile(filepath):
            os.remove(filepath)

    def get_cert_paths(self):
        paths = {}
        for kind, (content_attr, filename, _ldap_opt) in self.FILE_MAP[self.category].items():
            filepath = self.get_cert_file_path(filename)
            if os.path.isfile(filepath):
                paths[kind] = filepath
        return paths

    def sync_files(self, content_map=None):
        for kind, (content_attr, filename, _ldap_opt) in self.FILE_MAP[self.category].items():
            if content_map is not None and content_attr not in content_map:
                content = getattr(settings, content_attr, '') or ''
            elif content_map is not None:
                content = content_map.get(content_attr) or ''
            else:
                content = getattr(settings, content_attr, '') or ''
            if content:
                self.write_cert_file(filename, content)
            elif content_map is not None and content_attr in content_map:
                self.remove_cert_file(filename)

    def build_global_options(self):
        tls_require_cert = (
            ldap.OPT_X_TLS_DEMAND if CONFIG.VERIFY_EXTERNAL_SSL else ldap.OPT_X_TLS_NEVER
        )
        referrals_attr = f'{self.prefix}_OPTIONS_OPT_REFERRALS'
        options = {
            ldap.OPT_X_TLS_REQUIRE_CERT: tls_require_cert,
            ldap.OPT_REFERRALS: getattr(CONFIG, referrals_attr),
        }
        if self.tls_supports_cert_files():
            for kind, (content_attr, filename, ldap_opt) in self.FILE_MAP[self.category].items():
                filepath = self.get_cert_file_path(filename)
                if os.path.isfile(filepath):
                    options[ldap_opt] = filepath
        return options

    def refresh_global_options(self):
        global_options_attr = f'{self.prefix}_GLOBAL_OPTIONS'
        setattr(settings, global_options_attr, self.build_global_options())
