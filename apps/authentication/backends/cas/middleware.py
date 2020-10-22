from django_cas_ng.middleware import CASMiddleware as _CASMiddleware
from django.core.exceptions import MiddlewareNotUsed
from django.conf import settings


class CASMiddleware(_CASMiddleware):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not settings.AUTH_CAS:
            raise MiddlewareNotUsed
