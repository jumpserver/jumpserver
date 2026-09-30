"""Python client for credential access, event streams, and application commands."""

import logging
import math
from dataclasses import replace
from email.utils import formatdate
from threading import Event, Lock
from typing import Any, Callable, Iterable, Iterator, Optional, TypeVar
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests

from ._auth import HTTPSignatureAuth
from ._commands import execute_command
from ._event_dispatcher import EventDispatcher
from ._events import EventStream
from ._transport import Transport
from ._version import CONFIG_SCHEMA_VERSION, PROTOCOL_VERSION, __version__
from .exceptions import PAMError
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
logger = logging.getLogger(__name__)


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
        self.timeout = timeout
        self.source = source
        self.instance_id = instance_id
        self._app_id = app_id
        self._app_secret = app_secret
        self.auth = HTTPSignatureAuth(app_id, app_secret)
        self._transport = Transport()
        self._streams = set()
        self._streams_lock = Lock()
        self._events_lock = Lock()
        self._event_dispatcher = None
        self._closed = False
        self._credentials_lock = Lock()
        self._latest_credentials = {}
        self._credential_generation = 0

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
        try:
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
        except PAMError as error:
            if (
                error.status_code in (401, 403, 404)
                or error.code == "client_upgrade_required"
                or (error.status_code == 400 and error.code == "credential_not_found")
            ):
                with self._credentials_lock:
                    self._latest_credentials.clear()
                    self._credential_generation += 1
            raise

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
        allow_local_fallback: bool = True,
    ) -> Credential:
        """Fetch by policy key or pull-authorized account ID; supply exactly one.

        Retain the latest successful credential without expiry. Only temporary
        backend failures may return it with from_local=True. Use
        allow_local_fallback=False when applying an event or confirming a rotation.
        """
        if (key is None) == (account_id is None) or not all(
            isinstance(value, str) and value
            for value in (key, account_id)
            if value is not None
        ):
            raise ValueError("exactly one of key or account_id is required")
        if type(allow_local_fallback) is not bool:
            raise ValueError("allow_local_fallback must be a boolean")
        selector = ("key", key) if key is not None else ("account_id", account_id)
        with self._credentials_lock:
            generation = self._credential_generation
        try:
            credential = self._request(
                "GET",
                f"{CLIENT_PATH}/credential/",
                {"key": key, "account_id": account_id},
                Credential.from_dict,
                query=True,
            )
        except PAMError as error:
            denied = (
                error.status_code in (401, 403, 404)
                or error.code == "client_upgrade_required"
                or (error.status_code == 400 and error.code == "credential_not_found")
            )
            temporary = error.code == "NetworkError" or (
                error.status_code is not None and 500 <= error.status_code < 600
            )
            with self._credentials_lock:
                if denied:
                    self._latest_credentials.clear()
                    self._credential_generation += 1
                latest = self._latest_credentials.get(selector)
                if (
                    allow_local_fallback
                    and key is not None
                    and temporary
                    and not denied
                    and not self._closed
                    and latest
                ):
                    return replace(latest, from_local=True)
            raise
        with self._credentials_lock:
            if not self._closed and generation == self._credential_generation:
                latest = self._latest_credentials.get(selector)
                if latest is not None and credential.revision < latest.revision:
                    raise PAMError(
                        "ResponseError",
                        "Credential revision moved backwards",
                        status_code=200,
                    )
                self._latest_credentials[selector] = credential
        return credential

    def _reconcile_latest_credentials(self, event):
        name = event.get("event")
        if name not in {"snapshot", "credential.revoked", "configuration.updated"}:
            return
        with self._credentials_lock:
            self._credential_generation += 1
            if name == "configuration.updated":
                # Retain known credentials until a snapshot reconciles authorization.
                return
            if name != "snapshot":
                key = event.get("credential_key") or event.get("key")
                account_id = event.get("account_id")
                key = key if isinstance(key, str) and key else None
                account_id = (
                    account_id if isinstance(account_id, str) and account_id else None
                )
                if key is None and account_id is None:
                    self._latest_credentials.clear()
                else:
                    self._latest_credentials = {
                        selector: credential
                        for selector, credential in self._latest_credentials.items()
                        if not (
                            key is not None
                            and (
                                selector == ("key", key)
                                or credential.key == key
                                or credential.key.startswith(key + ":")
                            )
                            or account_id is not None
                            and (key is None or key.startswith("account:"))
                            and (
                                selector == ("account_id", account_id)
                                or credential.account.id == account_id
                            )
                        )
                    }
                return
            updates = event.get("credentials", [])
            if not isinstance(updates, list) or any(
                not isinstance(item, dict) for item in updates
            ):
                self._latest_credentials.clear()
                return
            keys = {
                value
                for item in updates
                if isinstance(
                    value := item.get("key") or item.get("credential_key"), str
                )
            }
            self._latest_credentials = {
                selector: credential
                for selector, credential in self._latest_credentials.items()
                if selector[0] != "key" or selector[1] in keys
            }

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
        """Reconcile retained and delivered revisions with the authorized scope."""
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
        """Construct a fresh client of the same type, without copying hook state.

        Subclasses with additional required constructor arguments must override
        this method. Cloning never starts an event listener.
        """
        return type(self)(
            self.endpoint,
            app_id=self._app_id,
            app_secret=self._app_secret,
            instance_id=self.instance_id,
            org_id=self.org_id,
            timeout=self.timeout,
            source=self.source,
        )

    def close(self) -> None:
        """Stop all active event streams and close the owned HTTP session."""
        with self._events_lock:
            with self._streams_lock:
                self._closed = True
                streams = tuple(self._streams)
            dispatcher = self._event_dispatcher
            if dispatcher is not None:
                dispatcher.request_stop()
        for stream in streams:
            stream.close()
        if dispatcher is not None:
            dispatcher.wait()
        self._transport.close()
        with self._credentials_lock:
            self._latest_credentials.clear()
            self._credential_generation += 1

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *_):
        self.close()

    def _start_event_dispatcher(self, stop_event, background):
        with self._events_lock:
            if self._closed:
                raise RuntimeError("Client is closed")
            if (
                self._event_dispatcher is not None
                and not self._event_dispatcher.finished.is_set()
            ):
                raise RuntimeError("An event listener is already running")
            dispatcher = EventDispatcher(self, stop_event)
            self._event_dispatcher = dispatcher
            dispatcher.start(background)
            return dispatcher

    def watch_events(self, stop_event: Optional[Event] = None) -> None:
        """Block while dispatching events to subclass hooks until stopped.

        The reader runs independently of the serial hooks. Initial and reconnect
        snapshots fetch current credentials; failed fetches or credential hooks
        retry with backoff. Confirmation remains the application's responsibility.
        """
        dispatcher = self._start_event_dispatcher(stop_event, background=False)
        dispatcher.run()

    def start_events(self, stop_event: Optional[Event] = None) -> None:
        """Start a background reader and serial hook worker, then return.

        Return does not mean the initial snapshot has been applied. Use an Event
        in your subclass if application startup must wait for its credentials.
        """
        self._start_event_dispatcher(stop_event, background=True)

    def stop_events(self) -> None:
        """Stop the hook listener and wait for active hooks; keep HTTP usable."""
        with self._events_lock:
            dispatcher = self._event_dispatcher
            if dispatcher is not None:
                dispatcher.request_stop()
        if dispatcher is not None:
            dispatcher.wait()

    def on_event(self, event: dict[str, Any]) -> None:
        """Observe each raw event before credential hooks, including snapshots.

        Override for snapshot cache cleanup, configuration changes, lifecycle
        events or application commands. This observer is not automatically retried.
        """

    def on_credential_changed(self, credential: Credential) -> None:
        """Apply a fetched credential; override with idempotent business logic.

        Called for subscription and rotation updates and every reconnect snapshot.
        Failures retry after fetching the current credential again. For rotation,
        confirm_credential must be called explicitly after a successful switch.
        """

    def on_credential_revoked(self, event: dict[str, Any]) -> None:
        """Override to stop using revoked credentials and release connections."""

    def on_event_error(self, error: Exception, event: Optional[dict[str, Any]]) -> None:
        """Handle hook/fetch failures; event is None for a fatal reader failure.

        Never log credential values or arbitrary exception messages.
        """
        self._log_event_error(error)

    @staticmethod
    def _log_event_error(error: Exception) -> None:
        logger.warning("Credential event handler failed: %s", type(error).__name__)

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
            for event in stream.watch(stop_event):
                self._reconcile_latest_credentials(event)
                yield event
        finally:
            stream.close()
            with self._streams_lock:
                self._streams.discard(stream)

    def _event_stream_url(self):
        endpoint = urlsplit(self.endpoint)
        scheme = "wss" if endpoint.scheme == "https" else "ws"
        params = {}
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
