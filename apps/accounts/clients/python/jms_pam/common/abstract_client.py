"""Compatibility adapter for the original Credential/ClientProfile API."""

import copy

from .._auth import SIGNATURE_HEADERS, HTTPSignatureAuth
from ..client import Client
from .abstract_model import AbstractModel
from .credential import Credential
from .profile.client_profile import ClientProfile

__all__ = ["AbstractClient", "HTTPSignatureAuth", "SIGNATURE_HEADERS"]


class AbstractClient(Client):
    def __init__(self, cred, instance_id, profile):
        if not isinstance(cred, Credential):
            raise TypeError("cred must be a Credential")
        if not isinstance(profile, ClientProfile):
            raise TypeError("profile must be a ClientProfile")
        self.credential = cred
        self.profile = profile
        super().__init__(
            profile.Endpoint,
            app_id=cred.AppId,
            app_secret=cred.AppSecret,
            instance_id=instance_id,
            org_id=profile.OrgId,
            timeout=profile.Timeout,
            source=profile.Source,
        )

    def _request(self, method, path, request, response_type, query=False):
        if isinstance(request, AbstractModel):
            request._validate()
            data = request._serialize()

            def parse(payload):
                return response_type()._deserialize(payload)._validate()
        else:
            data, parse = request, response_type
        return super()._request(method, path, data, parse, query)

    def clone(self):
        return type(self)(self.credential, self.instance_id, copy.copy(self.profile))

    @property
    def endpoint(self):
        return self.profile.Endpoint

    @endpoint.setter
    def endpoint(self, value):
        self.profile.Endpoint = value

    @property
    def org_id(self):
        return self.profile.OrgId

    @org_id.setter
    def org_id(self, value):
        self.profile.OrgId = value

    @property
    def timeout(self):
        return self.profile.Timeout

    @timeout.setter
    def timeout(self, value):
        self.profile.Timeout = value

    @property
    def source(self):
        return self.profile.Source

    @source.setter
    def source(self, value):
        self.profile.Source = value
