from django_cas_ng import utils
from django_cas_ng.utils import (
    django_settings, get_protocol,
    urllib_parse, REDIRECT_FIELD_NAME, get_redirect_url
)


def get_service_url(request, redirect_to=None):
    """
    重写 get_service url 方法, CAS_ROOT_PROXIED_AS 为空时, 支持跳转回当前访问的域名地址
    """
    """Generates application django service URL for CAS"""
    if getattr(django_settings, 'CAS_ROOT_PROXIED_AS', None):
        service = django_settings.CAS_ROOT_PROXIED_AS + request.path
    else:
        protocol = get_protocol(request)
        host = request.get_host()
        service = urllib_parse.urlunparse(
            (protocol, host, request.path, '', '', ''),
        )
    if not django_settings.CAS_STORE_NEXT:
        if '?' in service:
            service += '&'
        else:
            service += '?'
        service += urllib_parse.urlencode({
            REDIRECT_FIELD_NAME: redirect_to or get_redirect_url(request)
        })
    return service


utils.get_service_url = get_service_url
