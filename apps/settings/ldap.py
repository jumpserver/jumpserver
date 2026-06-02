import os
import ssl

import ldap
from django.conf import settings
from ldap3 import Tls


LDAP_CA_CERTIFICATE_FILENAMES = {
    'ldap': 'ldap_ca.pem',
    'ldap_ha': 'ldap_ha_ca.pem',
}
LDAP_CA_CERTIFICATE_MAX_SIZE = 1024 * 1024


def get_ldap_ca_certificate_path(category):
    try:
        filename = LDAP_CA_CERTIFICATE_FILENAMES[category]
    except KeyError:
        raise ValueError('Invalid LDAP category')
    return os.path.join(settings.CERTS_DIR, filename)


def get_ldap_ca_certificate_file(category):
    path = get_ldap_ca_certificate_path(category)
    return path if os.path.isfile(path) else None


def get_ldap_ignore_ssl_verification(category):
    key = f'AUTH_{category.upper()}_IGNORE_SSL_VERIFICATION'
    return getattr(settings, key, False) or not settings.VERIFY_EXTERNAL_SSL


def get_ldap3_tls(category, ignore_ssl_verification=None):
    if ignore_ssl_verification is None:
        ignore_ssl_verification = get_ldap_ignore_ssl_verification(category)
    validate = ssl.CERT_NONE if ignore_ssl_verification else ssl.CERT_REQUIRED
    return Tls(
        validate=validate,
        ca_certs_file=get_ldap_ca_certificate_file(category),
    )


def get_python_ldap_tls_options(category):
    ignore_ssl_verification = get_ldap_ignore_ssl_verification(category)
    require_cert = (
        ldap.OPT_X_TLS_NEVER
        if ignore_ssl_verification
        else ldap.OPT_X_TLS_DEMAND
    )
    options = {ldap.OPT_X_TLS_REQUIRE_CERT: require_cert}
    ca_cert_file = get_ldap_ca_certificate_file(category)
    if not ignore_ssl_verification and ca_cert_file:
        options[ldap.OPT_X_TLS_CACERTFILE] = ca_cert_file
    options[ldap.OPT_X_TLS_NEWCTX] = 0
    

    return options
