"""Python client for credential access, event streams, and application commands."""

import math
from email.utils import formatdate
from threading import Event, Lock
from typing import Any, Callable, Iterable, Iterator, Optional, TypeVar
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests

from ._auth import HTTPSignatureAuth
from ._commands import execute_command
from ._events import EventStream
from ._transport import Transport
from ._version import CONFIG_SCHEMA_VERSION, PROTOCOL_VERSION, __version__
from .models import (
    AgentSync,
    CommandResult,
    Credential,
    CredentialConfirmation,
    KnownRevision,
)

CLIENT_PATH = "/api/v1/accounts/credential-client"
DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000002"
Response = TypeVar("Response")


class Client:
    """A signed client for one application replica.

    Use a stable, unique instance_id and close the client when finished,
    preferably with a context manager. Each clone owns its HTTP session.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        app_id: str,
        app_secret: str,
        instance_id: str,
        org_id: str = DEFAULT_ORG_ID,
        configuration_id: Optional[str] = None,
        timeout: float = 10,
        source: str = "jms-pam",
    ):
        if not all(isinstance(value, str) and value for value in (app_id, app_secret)):
            raise ValueError("app_id and app_secret are required")
        if not isinstance(endpoint, str) or not endpoint:
            raise ValueError("endpoint must be a non-empty HTTP(S) URL")
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "endpoint must be an HTTP(S) URL without credentials, query or fragment"
            )
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be a positive finite number")
        if (
            not isinstance(instance_id, str)
            or not instance_id.strip()
            or instance_id != instance_id.strip()
            or len(instance_id) > 128
        ):
            raise ValueError(
                "instance_id must be a stable, unique ID with 1-128 characters "
                "and no surrounding whitespace"
            )
        self.endpoint = endpoint.rstrip("/")
        self.org_id = org_id
        self.configuration_id = configuration_id
        self.timeout = timeout
        self.source = source
        self.instance_id = instance_id
        self._app_id = app_id
        self._app_secret = app_secret
        self.auth = HTTPSignatureAuth(app_id, app_secret)
        self._transport = Transport()
        self._streams = set()
        self._streams_lock = Lock()
        self._closed = False

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any],
        parse: Callable[[dict[str, Any]], Response],
        query: bool = False,
    ) -> Response:
        data = {key: value for key, value in data.items() if value is not None}
        data["instance_id"] = self.instance_id
        if self.configuration_id:
            data["configuration_id"] = self.configuration_id
        return self._transport.request(
            method,
            f"{self.endpoint}{path}",
            parse,
            params=data if query else None,
            json=None if query else data,
            headers=self._headers(),
            auth=self.auth,
            timeout=self.timeout,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "X-JMS-ORG": self.org_id,
            "X-Source": self.source,
            "X-JMS-Client-Version": __version__,
            "X-JMS-Protocol-Version": str(PROTOCOL_VERSION),
            "X-JMS-Config-Schema-Version": (
                str(CONFIG_SCHEMA_VERSION) if self.source == "jms-pam-agent" else "0"
            ),
            "Date": formatdate(usegmt=True),
        }

    @property
    def session(self) -> requests.Session:
        """The owned session; use clone() when an independent session is needed."""
        return self._transport.session

    def get_credential(
        self,
        *,
        key: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> Credential:
        """Fetch by policy key or subscription account ID; supply exactly one."""
        if (key is None) == (account_id is None) or not all(
            isinstance(value, str) and value
            for value in (key, account_id)
            if value is not None
        ):
            raise ValueError("exactly one of key or account_id is required")
        return self._request(
            "GET",
            f"{CLIENT_PATH}/credential/",
            {"key": key, "account_id": account_id},
            Credential.from_dict,
            query=True,
        )

    def confirm_credential(
        self,
        *,
        key: str,
        revision: int,
        account_id: str,
    ) -> CredentialConfirmation:
        """Confirm only after the application has applied this account revision."""
        if (
            not all(isinstance(value, str) and value for value in (key, account_id))
            or type(revision) is not int
            or revision < 1
        ):
            raise ValueError(
                "key, account_id and a positive integer revision are required"
            )
        return self._request(
            "POST",
            f"{CLIENT_PATH}/confirm/",
            {"key": key, "revision": revision, "account_id": account_id},
            CredentialConfirmation.from_dict,
        )

    def sync_agent(
        self,
        *,
        credentials: Iterable[KnownRevision],
        delivered_credentials: Iterable[KnownRevision],
        config_digest: str = "",
        sync_status: str = "",
        sync_error: str = "",
    ) -> AgentSync:
        """Reconcile cached and delivered revisions with the authorized scope."""
        return self._request(
            "POST",
            f"{CLIENT_PATH}/agent/sync/",
            {
                "credentials": [item.to_dict() for item in credentials],
                "delivered_credentials": [
                    item.to_dict() for item in delivered_credentials
                ],
                "config_digest": config_digest,
                "sync_status": sync_status,
                "sync_error": sync_error,
            },
            AgentSync.from_dict,
        )

    def list_application_commands(self) -> list[dict[str, Any]]:
        """Return outstanding commands for this replica."""

        def parse(data):
            commands = data.get("commands")
            if not isinstance(commands, list) or not all(
                isinstance(command, dict) for command in commands
            ):
                raise TypeError("commands must be a list of objects")
            return commands

        return self._request(
            "GET",
            f"{CLIENT_PATH}/commands/",
            {},
            parse,
            query=True,
        )

    def report_application_command_result(
        self,
        *,
        command_id: str,
        status: str,
        error_code: Optional[str] = None,
    ) -> CommandResult:
        """Claim a command with running, then report its actual outcome."""
        if not command_id or status not in ("running", "success", "failed"):
            raise ValueError("command_id and a valid command status are required")
        return self._request(
            "POST",
            f"{CLIENT_PATH}/command-result/",
            {"command_id": command_id, "status": status, "error_code": error_code},
            CommandResult.from_dict,
        )

    def execute_application_command(
        self,
        event: dict[str, Any],
        handler: Callable[[dict[str, Any]], Any],
    ) -> CommandResult:
        """Claim once, run an application handler, then report its actual result."""
        return execute_command(event, handler, self.report_application_command_result)

    def clone(self) -> "Client":
        """Create an independent HTTP session for the same client identity."""
        return type(self)(
            self.endpoint,
            app_id=self._app_id,
            app_secret=self._app_secret,
            instance_id=self.instance_id,
            org_id=self.org_id,
            configuration_id=self.configuration_id,
            timeout=self.timeout,
            source=self.source,
        )

    def close(self) -> None:
        """Stop all active event streams and close the owned HTTP session."""
        with self._streams_lock:
            self._closed = True
            streams = tuple(self._streams)
        for stream in streams:
            stream.close()
        self._transport.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *_):
        self.close()

    def watch_credential_events(
        self,
        stop_event: Optional[Event] = None,
    ) -> Iterator[dict[str, Any]]:
        """Acknowledge received events before yielding; this is not an applied confirmation."""
        stream = EventStream(
            self._event_stream_url(), self._event_stream_headers, self.timeout
        )
        with self._streams_lock:
            if self._closed:
                raise RuntimeError("Client is closed")
            self._streams.add(stream)
        try:
            yield from stream.watch(stop_event)
        finally:
            stream.close()
            with self._streams_lock:
                self._streams.discard(stream)

    def _event_stream_url(self):
        endpoint = urlsplit(self.endpoint)
        scheme = "wss" if endpoint.scheme == "https" else "ws"
        params = {}
        if self.configuration_id:
            params["configuration_id"] = self.configuration_id
        params["instance_id"] = self.instance_id
        query = urlencode(params)
        return urlunsplit(
            (
                scheme,
                endpoint.netloc,
                f"{endpoint.path.rstrip('/')}/ws/accounts/credential-events/",
                query,
                "",
            )
        )

    def _event_stream_headers(self):
        headers = {**self._headers(), "X-JMS-Event-Receipts": "1"}
        prepared = requests.Request(
            "GET", self._event_stream_url(), headers=headers
        ).prepare()
        self.auth(prepared)
        return [f"{name}: {value}" for name, value in prepared.headers.items()]
