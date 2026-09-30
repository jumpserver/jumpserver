"""Subclass hooks with independent event reading and ordered credential delivery."""

from dataclasses import dataclass
from queue import Empty, Full, Queue
from threading import Event, Thread, current_thread
from time import monotonic
from typing import Any, Optional


@dataclass
class PendingCredential:
    update: dict[str, Any]
    event: dict[str, Any]
    delay: float
    due: float


class EventDispatcher:
    def __init__(self, client, stop_event: Optional[Event] = None):
        self.client = client
        self.stop_event = stop_event if stop_event is not None else Event()
        self.finished = Event()
        self.events = Queue(maxsize=128)
        self.pending = {}
        self.reader = Thread(target=self._read, name="jms-pam-event-reader")
        self.worker = None
        self.reader_error = None

    def start(self, background: bool) -> None:
        self.background = background
        self.worker = (
            Thread(target=self.run, name="jms-pam-event-handler")
            if background
            else current_thread()
        )
        try:
            self.reader.start()
            if background:
                self.worker.start()
        except BaseException:
            self.request_stop()
            if self.reader.ident is not None:
                self.reader.join()
            self.finished.set()
            raise

    def request_stop(self) -> None:
        self.stop_event.set()

    def wait(self) -> None:
        # A hook may stop or close its own client without joining itself.
        if current_thread() not in (self.worker, self.reader):
            self.finished.wait()
            if self.background and self.worker.ident is not None:
                self.worker.join()

    def _put(self, event) -> None:
        while not self.stop_event.is_set():
            try:
                self.events.put(event, timeout=0.1)
                return
            except Full:
                continue

    def _read(self) -> None:
        stream = None
        try:
            stream = self.client.watch_credential_events(self.stop_event)
            for event in stream:
                self._put(event)
                if self.stop_event.is_set():
                    break
        except Exception as error:
            self.reader_error = error
        finally:
            close = getattr(stream, "close", None)
            if close is not None:
                try:
                    close()
                except Exception as error:
                    self.reader_error = error
            self._put(None)

    def _report_error(self, error, event) -> None:
        try:
            self.client.on_event_error(error, event)
        except Exception as hook_error:
            # Both exception messages and event payloads can contain secrets.
            self.client._log_event_error(hook_error)

    def _call(self, handler, value, event) -> None:
        try:
            handler(value)
        except Exception as error:
            self._report_error(error, event)

    @staticmethod
    def _selector(update):
        mode = update.get("credential_mode")
        if mode == "subscription":
            account_id = update.get("account_id")
            key = update.get("credential_key") or update.get("key")
            if isinstance(key, str) and key and isinstance(account_id, str) and account_id:
                if not key.endswith(f":{account_id}"):
                    key = f"{key}:{account_id}"
                return "key", key
        elif mode == "alternating_rotation":
            key = update.get("credential_key") or update.get("key")
            if isinstance(key, str) and key:
                return "key", key
        return None

    def _refresh(self, update, event, delay=0) -> None:
        if self.stop_event.is_set():
            return
        selector = self._selector(update)
        if selector is None:
            return
        previous = self.pending.get(selector)
        if previous is not None:
            previous_revision = previous.update.get("revision")
            revision = update.get("revision")
            if (
                type(previous_revision) is int
                and type(revision) is int
                and previous_revision > revision
            ):
                return
        try:
            credential = self.client.get_credential(
                **{selector[0]: selector[1]}, allow_local_fallback=False
            )
            expected = update.get("revision")
            if type(expected) is int and credential.revision < expected:
                raise ValueError("Credential API revision is behind the event")
            if self.stop_event.is_set():
                return
            self.client.on_credential_changed(credential)
        except Exception as error:
            self._report_error(error, event)
            delay = min(max(1, delay * 2), 30)
            self.pending[selector] = PendingCredential(
                update, event, delay, monotonic() + delay
            )
        else:
            self.pending.pop(selector, None)

    def _dispatch(self, event) -> None:
        name = event.get("event")
        if name in {"snapshot", "credential.revoked", "configuration.updated"}:
            # The following snapshot supplies the currently authorized scope.
            self.pending.clear()
        self._call(self.client.on_event, event, event)
        if self.stop_event.is_set():
            return
        if name == "snapshot":
            for update in event.get("credentials", []):
                try:
                    self._refresh(update, event)
                except Exception as error:
                    self._report_error(error, event)
        elif name == "credential.updated" and not event.get("command_id"):
            self._refresh(event, event)
        elif name == "credential.revoked":
            self._call(self.client.on_credential_revoked, event, event)

    def _retry(self) -> None:
        # Retry at most one credential between events so newer messages can run.
        if not self.pending:
            return
        selector = min(self.pending, key=lambda key: self.pending[key].due)
        pending = self.pending[selector]
        if pending.due <= monotonic():
            self._refresh(pending.update, pending.event, pending.delay)

    def run(self) -> None:
        try:
            while not self.stop_event.is_set():
                try:
                    event = self.events.get(timeout=0.1)
                except Empty:
                    self._retry()
                    continue
                if event is None:
                    if self.reader_error is not None:
                        self._report_error(self.reader_error, None)
                    break
                try:
                    self._dispatch(event)
                except Exception as error:
                    self._report_error(error, event)
                self._retry()
        finally:
            self.request_stop()
            self.reader.join()
            self.pending.clear()
            while not self.events.empty():
                self.events.get_nowait()
            self.finished.set()
