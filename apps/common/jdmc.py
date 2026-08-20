from django.conf import settings

import requests_unixsocket


__all__ = ['request_jdmc']


def request_jdmc(method='GET', path='', timeout=(5, 60), **kwargs):
    """Request the trusted JDMC/KOTL API over its Unix socket."""
    url = settings.JDMC_BASE_URL + path
    with requests_unixsocket.Session() as session:
        return session.request(method, url, timeout=timeout, **kwargs)
