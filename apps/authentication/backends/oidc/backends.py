from jms_oidc_rp import backends
from ..mixins import ModelBackendMixin


class OIDCAuthCodeBackend(ModelBackendMixin, backends.OIDCAuthCodeBackend):
    pass


class OIDCAuthPasswordBackend(ModelBackendMixin, backends.OIDCAuthPasswordBackend):
    pass
