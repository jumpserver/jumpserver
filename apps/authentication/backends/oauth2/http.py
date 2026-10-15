from django.conf import settings

from authentication.backends.http import create_http_session


OAUTH2_HTTP_TIMEOUT = (5, 30)


def create_oauth2_session():
    return create_http_session(
        settings.AUTH_OAUTH2_CERT_VERIFY_MODE,
        settings.AUTH_OAUTH2_CACERT_CONTENT,
    )
