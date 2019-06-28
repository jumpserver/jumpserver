#  coding: utf-8
#

import warnings
import contextlib

import requests
from urllib3.exceptions import InsecureRequestWarning
from django.conf import settings

old_merge_environment_settings = requests.Session.merge_environment_settings

__all__ = [
    'ssl_verification',
]


@contextlib.contextmanager
def no_ssl_verification():
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings

        for adapter in opened_adapters:
            try:
                adapter.close()
            except:
                pass


def ssl_verification(func):
    def wrapper(*args, **kwargs):
        if settings.AUTH_OPENID_NEED_SSL_VERIFICATION:
            return func(*args, **kwargs)
        with no_ssl_verification():
            return func(*args, **kwargs)
    return wrapper
