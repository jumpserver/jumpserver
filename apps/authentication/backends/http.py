import ssl

import requests
from requests.adapters import HTTPAdapter


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

    def cert_verify(self, conn, url, verify, cert):
        # The SSL context already contains the system trust store plus any
        # configured CA. Let Requests retain its normal client-cert handling.
        if cert:
            return super().cert_verify(conn, url, verify, cert)


def create_http_session(verify_mode, ca_cert=''):
    session = requests.Session()

    if verify_mode in ('system', 'custom_ca'):
        context = ssl.create_default_context()
        if verify_mode == 'custom_ca':
            context.load_verify_locations(cadata=ca_cert)
        session.mount('https://', SSLContextAdapter(context))
    elif verify_mode == 'none':
        session.verify = False
    else:
        session.close()
        raise ValueError('Unsupported certificate verification mode')

    return session
