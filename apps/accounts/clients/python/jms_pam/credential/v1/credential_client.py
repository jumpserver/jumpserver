"""Deprecated compatibility API; new integrations should use jms_pam.Client."""

import warnings

import websocket as websocket  # Kept for applications that patch the original module.

from ..._commands import execute_command
from ...client import CLIENT_PATH
from ...common.abstract_client import AbstractClient
from ...models import CommandResult
from . import models


class CredentialClient(AbstractClient):
    def _call(self, method, path, request, request_type, response_type, query=False):
        warnings.warn(
            "The request-object API is deprecated; use jms_pam.Client keyword methods.",
            DeprecationWarning,
            stacklevel=3,
        )
        if not isinstance(request, request_type):
            raise TypeError(f"request must be a {request_type.__name__}")
        return self._request(
            method, f"{CLIENT_PATH}/{path}/", request, response_type, query
        )

    def GetCredential(self, request):
        return self._call(
            "GET",
            "credential",
            request,
            models.GetCredentialRequest,
            models.GetCredentialResponse,
            query=True,
        )

    def ConfirmCredential(self, request):
        return self._call(
            "POST",
            "confirm",
            request,
            models.ConfirmCredentialRequest,
            models.ConfirmCredentialResponse,
        )

    def SyncAgent(self, request):
        return self._call(
            "POST",
            "agent/sync",
            request,
            models.AgentSyncRequest,
            models.AgentSyncResponse,
        )

    def ListApplicationCommands(self):
        return self._call(
            "GET",
            "commands",
            models.ListApplicationCommandsRequest(),
            models.ListApplicationCommandsRequest,
            models.ListApplicationCommandsResponse,
            query=True,
        )

    def ReportApplicationCommandResult(self, request):
        return self._call(
            "POST",
            "command-result",
            request,
            models.ApplicationCommandResultRequest,
            models.ApplicationCommandResultResponse,
        )

    def ExecuteApplicationCommand(self, event, handler):
        """Compatibility wrapper around the shared command lifecycle."""

        def report(*, command_id, status, error_code=None):
            result = self.ReportApplicationCommandResult(
                models.ApplicationCommandResultRequest(
                    CommandId=command_id, Status=status, ErrorCode=error_code
                )
            )
            return CommandResult.from_dict(
                {"accepted": result.Accepted, "status": result.Status}
            )

        result = execute_command(event, handler, report)
        return models.ApplicationCommandResultResponse(
            Accepted=result.accepted, Status=result.status
        )

    def WatchCredentialEvents(self, stop_event=None):
        warnings.warn(
            "WatchCredentialEvents is deprecated; use watch_credential_events.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.watch_credential_events(stop_event)
