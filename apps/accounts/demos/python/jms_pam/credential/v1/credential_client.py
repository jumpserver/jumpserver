from ...common.abstract_client import AbstractClient
from . import models

CLIENT_PATH = '/api/v1/accounts/credential-client'


class CredentialClient(AbstractClient):
    def _call(self, method, path, request, request_type, response_type, query=False):
        if not isinstance(request, request_type):
            raise TypeError(f'request must be a {request_type.__name__}')
        return self._request(method, f'{CLIENT_PATH}/{path}/', request, response_type, query)

    def GetCredential(self, request):
        return self._call(
            'GET', 'credential', request, models.GetCredentialRequest,
            models.GetCredentialResponse, query=True,
        )

    def ConfirmCredential(self, request):
        return self._call(
            'POST', 'confirm', request, models.ConfirmCredentialRequest,
            models.ConfirmCredentialResponse,
        )

    def Heartbeat(self, request):
        return self._call(
            'POST', 'heartbeat', request, models.HeartbeatRequest,
            models.HeartbeatResponse,
        )

    def SyncAgent(self, request):
        return self._call(
            'POST', 'agent/sync', request, models.AgentSyncRequest,
            models.AgentSyncResponse,
        )
