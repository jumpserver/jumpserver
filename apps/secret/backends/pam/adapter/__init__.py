from django.conf import settings
from common.utils import get_logger

from .adapters import JSONAdapter

logger = get_logger(__name__)

__all__ = ['Client', ]


class Client(object):

    def __init__(
            self,
            url=None,
            cert=None,
            verify=None,
            timeout=30,
            proxies=None,
            allow_redirects=True,
            session=None,
            adapter=JSONAdapter,
            namespace=None,
            **kwargs
    ):
        url = url if url else settings.PAM_URL

        if not verify:
            verify = True

        self._adapter = adapter(
            base_uri=url,
            cert=cert,
            verify=verify,
            timeout=timeout,
            proxies=proxies,
            allow_redirects=allow_redirects,
            session=session,
            namespace=namespace,
            **kwargs
        )

    @property
    def adapter(self):
        return self._adapter

    @adapter.setter
    def adapter(self, adapter):
        self._adapter = adapter

    @property
    def url(self):
        return self._adapter.base_uri

    @url.setter
    def url(self, url):
        self._adapter.base_uri = url

    @property
    def session(self):
        return self._adapter.session

    @session.setter
    def session(self, session):
        self._adapter.session = session

    @property
    def allow_redirects(self):
        return self._adapter.allow_redirects

    @allow_redirects.setter
    def allow_redirects(self, allow_redirects):
        self._adapter.allow_redirects = allow_redirects
