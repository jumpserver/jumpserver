from jms_oidc_rp.middleware import OIDCRefreshIDTokenMiddleware as _OIDCRefreshIDTokenMiddleware
from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings


class OIDCRefreshIDTokenMiddleware(_OIDCRefreshIDTokenMiddleware):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not settings.AUTH_OPENID:
            raise MiddlewareNotUsed
