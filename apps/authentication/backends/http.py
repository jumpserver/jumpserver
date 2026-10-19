import ssl

import requests
from requests.adapters import HTTPAdapter


class TLSConfigurationError(ValueError):
    pass


class SSLContextAdapter(HTTPAdapter):
    """Use a caller-provided SSL context without changing global HTTP state."""

    def __init__(self, ssl_context, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(connections, maxsize, block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_kwargs['ssl_context'] = self.ssl_context
        return super().proxy_manager_for(proxy, **proxy_kwargs)

    def build_connection_pool_key_attributes(self, request, verify, cert=None):
        host_params, pool_kwargs = super().build_connection_pool_key_attributes(
            request, verify, cert
        )
        pool_kwargs['ssl_context'] = self.ssl_context
        if self.ssl_context.verify_mode == ssl.CERT_NONE:
            # Requests may turn REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE into CA
            # parameters before the adapter sees the request. In insecure mode
            # they must not override CERT_NONE or load trust anchors.
            pool_kwargs.pop('ca_certs', None)
            pool_kwargs.pop('ca_cert_dir', None)
            pool_kwargs.pop('ca_cert_data', None)
            pool_kwargs['cert_reqs'] = ssl.CERT_NONE
        return host_params, pool_kwargs

    def cert_verify(self, conn, url, verify, cert):
        # Verification is fully configured by the caller-provided SSLContext.
        # Calling the parent implementation would mutate the selected pool
        # with Requests' CA bundle after its pool key has already been built.
        return


def create_http_session(verify_mode, ca_cert=''):
    session = requests.Session()

    if verify_mode not in ('system', 'custom_ca', 'none'):
        session.close()
        raise TLSConfigurationError('Unsupported certificate verification mode')

    try:
        context = ssl.create_default_context()
        if verify_mode == 'custom_ca':
            context.load_verify_locations(cadata=ca_cert)
        elif verify_mode == 'none':
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            session.verify = False
    except (ssl.SSLError, TypeError, ValueError) as exc:
        session.close()
        raise TLSConfigurationError('Invalid TLS configuration') from exc

    session.mount('https://', SSLContextAdapter(context))

    return session
