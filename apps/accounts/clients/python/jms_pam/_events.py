"""Credential event delivery, receipts, reconnects and cancellation."""

import json
import logging
from threading import Event, Lock
from time import monotonic
from typing import Any, Callable, Iterator, Optional

import websocket

logger = logging.getLogger(__name__)


class EventStream:
    def __init__(self, url: str, headers: Callable[[], list[str]], timeout: float):
        self.url = url
        self.headers = headers
        self.timeout = timeout
        self._closed = Event()
        self._lock = Lock()
        self._connection = None

    def _stopped(self, stop_event):
        return self._closed.is_set() or (stop_event is not None and stop_event.is_set())

    def _wait(self, delay, stop_event):
        # Both client.close() and the caller's event can interrupt backoff.
        remaining = delay
        while remaining > 0 and not self._stopped(stop_event):
            interval = min(remaining, 0.1)
            self._closed.wait(interval)
            remaining -= interval

    def _disconnect(self):
        with self._lock:
            connection, self._connection = self._connection, None
        if connection is not None:
            try:
                connection.close()
            except (OSError, websocket.WebSocketException):
                pass

    def close(self) -> None:
        self._closed.set()
        self._disconnect()

    def watch(self, stop_event: Optional[Event] = None) -> Iterator[dict[str, Any]]:
        delay = 1
        try:
            while not self._stopped(stop_event):
                try:
                    connection = websocket.create_connection(
                        self.url, header=self.headers(), timeout=self.timeout
                    )
                    with self._lock:
                        self._connection = connection
                    if self._stopped(stop_event):
                        return
                    connection.settimeout(min(self.timeout, 1))
                    next_ping = 0
                    while not self._stopped(stop_event):
                        try:
                            payload = connection.recv()
                        except websocket.WebSocketTimeoutException:
                            now = monotonic()
                            if now >= next_ping:
                                connection.send(json.dumps({"event": "ping"}))
                                next_ping = now + 10
                            continue
                        if not payload:
                            break
                        event = json.loads(payload)
                        if not isinstance(event, dict) or not isinstance(
                            event.get("event"), str
                        ):
                            raise ValueError("Invalid credential event message")
                        # Reset only after a valid message, not an immediately closed connection.
                        delay = 1
                        if event["event"] == "pong":
                            continue
                        if event["event"] != "snapshot" and event.get("event_id"):
                            try:
                                connection.send(
                                    json.dumps(
                                        {
                                            "event": "received",
                                            "event_id": event["event_id"],
                                        }
                                    )
                                )
                            except (OSError, websocket.WebSocketException):
                                pass
                        yield event
                except (OSError, ValueError, websocket.WebSocketException) as error:
                    # Exception text can contain server-provided credential data.
                    logger.warning(
                        "Credential event stream disconnected: %s", type(error).__name__
                    )
                finally:
                    self._disconnect()
                self._wait(delay, stop_event)
                delay = min(delay * 2, 30)
        finally:
            self.close()
