import urllib3
import requests
import requests.exceptions
from abc import ABCMeta, abstractmethod

from . import utils

urllib3.disable_warnings()


class Adapter(object):
    __metaclass__ = ABCMeta

    def __init__(
            self,
            base_uri='',
            cert=None,
            verify=True,
            timeout=30,
            proxies=None,
            allow_redirects=True,
            session=None,
            namespace=None,
            ignore_exceptions=False
    ):
        if not session:
            session = requests.Session()
            session.cert, session.verify, session.proxies = cert, verify, proxies

        self.base_uri = base_uri
        self.namespace = namespace
        self.session = session
        self.allow_redirects = allow_redirects
        self.ignore_exceptions = ignore_exceptions

        self._kwargs = {
            "cert": cert,
            "verify": verify,
            "timeout": timeout,
            "proxies": proxies,
        }

    def close(self):
        """Close the underlying Requests session."""
        self.session.close()

    def get(self, url, **kwargs):
        """Performs a GET request."""
        return self.request("get", url, **kwargs)

    def post(self, url, **kwargs):
        """Performs a POST request."""
        return self.request("post", url, **kwargs)

    def put(self, url, **kwargs):
        """Performs a PUT request."""
        return self.request("put", url, **kwargs)

    def delete(self, url, **kwargs):
        """Performs a DELETE request."""
        return self.request("delete", url, **kwargs)

    def head(self, url, **kwargs):
        """Performs a HEAD request."""
        return self.request("head", url, **kwargs)

    @abstractmethod
    def request(self, method, url, headers=None, raise_exception=True, **kwargs):
        raise NotImplementedError


class RawAdapter(Adapter):
    """
    The RawAdapter adapter class.
    """

    def request(self, method, url, headers=None, raise_exception=True, **kwargs):

        url = self.base_uri + url

        if not headers:
            headers = {}

        _kwargs = self._kwargs.copy()
        _kwargs.update(kwargs)

        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            allow_redirects=self.allow_redirects,
            **_kwargs
        )

        if not response.ok and (raise_exception and not self.ignore_exceptions):
            text = errors = None
            if response.headers.get("Content-Type") == "application/json":
                try:
                    errors = response.json().get("errors")
                except Exception:
                    pass
            if errors is None:
                text = response.text
            utils.raise_for_error(
                method, url, response.status_code, text, errors=errors
            )

        return response


class JSONAdapter(RawAdapter):
    """
    The JSONAdapter adapter class.
    """

    def request(self, *args, **kwargs):
        response = super().request(*args, **kwargs)
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                pass

        return response
