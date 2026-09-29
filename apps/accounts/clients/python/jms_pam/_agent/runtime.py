"""Credential reconciliation, application confirmations and command handling."""

import logging
import math
import subprocess
import threading
import time
from pathlib import Path
from queue import Empty, Full, Queue

from .._commands import report_failure
from ..client import Client
from ..exceptions import REVOKED_CODES, PAMError, identity_denied, response_error_code
from ..models import KnownRevision
from .config import CONFIG_FILE, CREDENTIAL_FILE, STATE_FILE, validate_configuration
from .delivery import deliver_credentials, flatten_credential
from .server import start_local_server
from .storage import atomic_write_json, read_json

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = read_json(config_file)
        self.capabilities = self.config["capabilities"]
        self.configuration = self.config["configuration"]
        validate_configuration(self.configuration, self.capabilities)
        self.state = read_json(self.config.get("state_file", STATE_FILE))
        self.credentials = read_json(
            self.config.get("credential_file", CREDENTIAL_FILE)
        )
        self.delivered = read_json(self.delivery_file)
        self.authorized_keys = set(
            self.config.get("authorized_keys", self.configuration["credential_keys"])
        )
        self.confirmation_keys = set(
            self.configuration.get(
                "confirmation_keys", self.configuration["credential_keys"]
            )
        )
        self.access_denied = bool(self.config.get("access_denied", False))
        application_access = "app_id" in self.config
        self.remote = Client(
            self.config["endpoint"],
            app_id=self.config["app_id"]
            if application_access
            else self.config["agent_id"],
            app_secret=self.config["app_secret"]
            if application_access
            else self.config["agent_secret"],
            instance_id=self.config.get("instance_id") or self.config.get("agent_id"),
            org_id=self.config["org_id"],
            source="jms-pam-agent",
            configuration_id=self.config.get("configuration_id")
            if application_access
            else None,
        )
        self.lock = threading.Lock()
        self.sync_lock = threading.RLock()

    @property
    def state_file(self):
        return self.config.get("state_file", STATE_FILE)

    @property
    def credential_file(self):
        return self.config.get("credential_file", CREDENTIAL_FILE)

    @property
    def delivery_file(self):
        default = str(Path(self.state_file).with_name("delivered.json"))
        return self.config.get("delivery_file", default)

    def save_config(self):
        atomic_write_json(self.config_file, self.config)

    def set_access_denied(self, denied, reason=""):
        with self.lock:
            if (
                self.access_denied == denied
                and self.config.get("denied_reason", "") == reason
            ):
                return
            self.access_denied = denied
            self.config["access_denied"] = denied
            self.config["denied_reason"] = reason
            self.save_config()

    def fetch(self, keys):
        fetched = {}
        revoked = set()
        for key in keys:
            try:
                response = self.remote.get_credential(key=key)
                if response.key != key:
                    raise PAMError(
                        "ResponseError", "Fetched credential key does not match"
                    )
                fetched[key] = flatten_credential(response)
            except (PAMError, OSError) as error:
                if identity_denied(error) or getattr(error, "status_code", None) == 426:
                    raise
                code = response_error_code(error)
                if code in REVOKED_CODES:
                    revoked.add(key)
                logger.warning(
                    "Agent credential %s: %s", key, code or type(error).__name__
                )
        if not fetched and not revoked:
            return set()
        with self.lock:
            if revoked:
                self.authorized_keys.difference_update(revoked)
                self.config["authorized_keys"] = sorted(self.authorized_keys)
                self.save_config()
            values = dict(self.credentials)
            changed = {
                key
                for key, item in fetched.items()
                if values.get(key, {}).get("revision") != item["revision"]
            }
            values.update(fetched)
            if values != self.credentials:
                atomic_write_json(self.credential_file, values)
                self.credentials = values
        return changed

    def deliver(self, changed):
        if not changed:
            return
        with self.lock:
            if self.access_denied or not set(changed) <= self.authorized_keys:
                raise PermissionError("Credential access was revoked")
            items = {key: dict(self.credentials[key]) for key in sorted(changed)}
            configuration = dict(self.configuration)
        deliver_credentials(items, configuration)
        with self.lock:
            delivered = dict(self.delivered)
            delivered.update(
                {
                    key: {"key": key, "revision": item["revision"]}
                    for key, item in items.items()
                }
            )
            atomic_write_json(self.delivery_file, delivered)
            self.delivered = delivered

    def sync(self, refresh_keys=()):
        """Serialize reconciliation and retain the last working credentials on errors."""
        with self.sync_lock:
            try:
                return self._sync(refresh_keys)
            except Exception as error:
                if (
                    identity_denied(error)
                    or response_error_code(error) in REVOKED_CODES
                    or getattr(error, "status_code", None) == 426
                ):
                    try:
                        self.set_access_denied(True, error.code)
                    except OSError:
                        logger.warning("Could not persist Agent access denial")
                with self.lock:
                    self.config["sync_status"] = "error"
                    self.config["sync_error"] = type(error).__name__
                    try:
                        self.save_config()
                    except OSError:
                        logger.warning("Could not persist Agent sync failure")
                raise

    def _sync(self, refresh_keys):
        with self.lock:
            known = [
                KnownRevision(key, item.get("revision", 0))
                for key, item in sorted(self.credentials.items())
            ]
            delivered = [
                KnownRevision(key, item.get("revision", 0))
                for key, item in sorted(self.delivered.items())
                if key in self.authorized_keys
            ]
            options = {
                name: self.config.get(name, "")
                for name in ("config_digest", "sync_status", "sync_error")
            }
        response = self.remote.sync_agent(
            credentials=known, delivered_credentials=delivered, **options
        )
        metadata = {item.key: item for item in response.credentials}
        configuration = response.configuration
        # Scope changes take effect even if the new delivery configuration is invalid.
        with self.lock:
            self.authorized_keys = set(metadata)
            self.config["authorized_keys"] = sorted(self.authorized_keys)
        if configuration is not None:
            validate_configuration(configuration, self.capabilities)
            with self.lock:
                self.configuration = dict(configuration)
                self.confirmation_keys = set(configuration.get("confirmation_keys", []))
                self.config["configuration"] = self.configuration
        refresh_keys = set(refresh_keys)
        keys = [
            key
            for key, item in metadata.items()
            if item.available
            and (
                key in refresh_keys
                or item.changed
                or self.credentials.get(key, {}).get("revision") != item.revision
            )
        ]
        self.fetch(keys)
        pending = {
            key
            for key, item in metadata.items()
            if key in self.authorized_keys
            and item.available
            and self.credentials.get(key, {}).get("revision") == item.revision
            and (
                configuration is not None
                or self.delivered.get(key, {}).get("revision") != item.revision
            )
        }
        # A successful signed sync restores local access before delivery.
        self.set_access_denied(False)
        self.deliver(pending)
        with self.lock:
            self.config.update(
                config_digest=response.config_digest,
                sync_status="success",
                sync_error="",
            )
            self.save_config()
        self.report_confirmations()
        return response

    def report_confirmations(self):
        with self.lock:
            if self.access_denied:
                return
            states = [
                dict(item)
                for key, item in sorted(self.state.items())
                if key in self.authorized_keys
                and key in getattr(self, "confirmation_keys", self.authorized_keys)
                and self.credentials.get(key, {}).get("revision")
                == item.get("revision")
                and self.credentials.get(key, {}).get("account_id")
                == item.get("account_id")
            ]
        for item in states:
            try:
                self.remote.confirm_credential(
                    key=item["key"],
                    revision=item["revision"],
                    account_id=item["account_id"],
                )
            except (PAMError, OSError):
                continue

    def finish_switch_command(self, event):
        key = event["credential_key"]
        with self.lock:
            if self.access_denied or key not in self.authorized_keys:
                return
            applied = dict(self.state.get(key, {}))
            cached = dict(self.credentials.get(key, {}))
        if (
            cached.get("revision") == event["revision"]
            and cached.get("account_id") == event["account_id"]
            and applied.get("revision") == event["revision"]
            and applied.get("account_id") == event["account_id"]
        ):
            self.report_confirmations()
            self.remote.report_application_command_result(
                command_id=event["command_id"], status="success"
            )

    def handle_command(self, event):
        with self.sync_lock:
            return self._handle_command(event)

    def _handle_command(self, event):
        claim = self.remote.report_application_command_result(
            command_id=event["command_id"], status="running"
        )
        if not claim.accepted:
            if (
                claim.status == "running"
                and event["event"] == "credential.switch.requested"
            ):
                self.finish_switch_command(event)
            return
        try:
            if event["event"] == "application.restart.requested":
                # Only the service and action allowed by the local bootstrap can run.
                validate_configuration(self.configuration, self.capabilities)
                if (
                    self.configuration["delivery_mode"] != "environment"
                    or self.configuration["systemd_action"] != "restart"
                ):
                    raise ValueError("Application restart is not configured")
                subprocess.run(
                    ["systemctl", "restart", self.configuration["systemd_unit"]],
                    check=True,
                    timeout=120,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    [
                        "systemctl",
                        "is-active",
                        "--quiet",
                        self.configuration["systemd_unit"],
                    ],
                    check=True,
                    timeout=30,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.remote.report_application_command_result(
                    command_id=event["command_id"], status="success"
                )
            elif event["event"] == "credential.switch.requested":
                self.sync()
                key = event["credential_key"]
                if key not in self.authorized_keys:
                    raise PermissionError("Credential access was revoked")
                self.fetch([key])
                item = self.credentials.get(key, {})
                if (
                    item.get("revision") != event["revision"]
                    or item.get("account_id") != event["account_id"]
                ):
                    raise ValueError("Requested account version is superseded")
                self.deliver({key})
                self.finish_switch_command(event)
            else:
                raise ValueError("Unsupported application command")
        except Exception:
            report_failure(
                self.remote.report_application_command_result, event["command_id"]
            )
            raise

    def process_commands(self):
        for event in self.remote.list_application_commands():
            try:
                self.handle_command(event)
            except Exception as error:
                logger.warning("Agent command failed: %s", type(error).__name__)

    def confirm(self, key, revision):
        with self.lock:
            if self.access_denied:
                raise PermissionError(
                    self.config.get("denied_reason") or "Agent access is disabled."
                )
            if key not in self.authorized_keys:
                raise KeyError(f"Credential not authorized: {key}")
            if key not in getattr(self, "confirmation_keys", self.authorized_keys):
                raise ValueError(
                    "Credential change subscriptions do not require confirmation."
                )
            item = self.credentials.get(key)
            if not item:
                raise KeyError(f"Credential not found: {key}")
            if type(revision) is not int or revision != item["revision"]:
                raise ValueError("Confirm the exact revision used by the application.")
            state = dict(self.state)
            state[key] = {
                "key": key,
                "revision": item["revision"],
                "account_id": item["account_id"],
            }
            atomic_write_json(self.state_file, state)
            self.state = state
        try:
            self.remote.confirm_credential(
                key=key, revision=item["revision"], account_id=item["account_id"]
            )
            status = "confirmed"
        except (PAMError, OSError):
            status = "pending"
        return {**state[key], "status": status}

    def safe_sync(self, refresh_keys=()):
        """Retained as a compatibility alias; notifications are never silently skipped."""
        return self.sync(refresh_keys=refresh_keys)

    def start_local_server(self):
        return start_local_server(self)

    def health(self):
        with self.lock:
            return {
                "status": "denied" if self.access_denied else "ok",
                "sync_status": self.config.get("sync_status", ""),
            }

    def local_credential(self, key):
        with self.lock:
            if self.access_denied:
                raise PermissionError(
                    self.config.get("denied_reason") or "agent_access_denied"
                )
            if key not in self.authorized_keys:
                raise KeyError("credential_not_authorized")
            if key not in self.credentials:
                raise KeyError("credential_not_available")
            return dict(self.credentials[key])

    def _reconcile(self):
        self.safe_sync()
        self.process_commands()

    def _handle_event(self, event):
        if event.get("command_id"):
            self.handle_command(event)
        elif event.get("event") in {
            "snapshot",
            "credential.updated",
            "credential.revoked",
            "configuration.updated",
        }:
            keys = (
                [event["credential_key"]]
                if event["event"] == "credential.updated"
                and event.get("credential_key")
                else []
            )
            self.safe_sync(refresh_keys=keys)

    def _read_events(self, stop, events):
        stream = None
        try:
            stream = self.remote.watch_credential_events(stop)
            for event in stream:
                if not self._enqueue(events, event, stop):
                    break
        except Exception as error:
            logger.warning("Agent event reader failed: %s", type(error).__name__)
        finally:
            close = getattr(stream, "close", None)
            if close is not None:
                try:
                    close()
                except Exception as error:
                    logger.warning("Agent event close failed: %s", type(error).__name__)
            self._enqueue(events, None, stop)

    @staticmethod
    def _enqueue(events, event, stop):
        while not stop.is_set():
            try:
                events.put(event, timeout=0.5)
                return True
            except Full:
                continue
        return False

    def run(self, stop_event=None):
        """Run one reconciliation worker; the reader only queues received events."""
        stop = stop_event if stop_event is not None else threading.Event()
        interval = self.config.get("reconcile_interval", 300)
        if (
            isinstance(interval, bool)
            or not isinstance(interval, (int, float))
            or not math.isfinite(interval)
            or interval <= 0
        ):
            raise ValueError("reconcile_interval must be positive")
        events = Queue(maxsize=128)
        try:
            server = self.start_local_server()
        except Exception:
            self.remote.close()
            raise
        reader = threading.Thread(
            target=self._read_events, args=(stop, events), name="jms-pam-events"
        )
        try:
            reader.start()
            try:
                self._reconcile()
            except Exception as error:
                logger.warning("Agent initial sync failed: %s", type(error).__name__)
            next_sync = time.monotonic() + interval
            while not stop.is_set():
                remaining = next_sync - time.monotonic()
                if remaining <= 0:
                    try:
                        self._reconcile()
                    except Exception as error:
                        logger.warning(
                            "Agent reconciliation failed: %s", type(error).__name__
                        )
                    next_sync = time.monotonic() + interval
                    continue
                try:
                    event = events.get(timeout=min(remaining, 0.5))
                except Empty:
                    continue
                if event is None:
                    break
                try:
                    self._handle_event(event)
                except Exception as error:
                    logger.warning("Agent event failed: %s", type(error).__name__)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            server.shutdown()
            self.remote.close()
            server.server_close()
            if reader.ident is not None:
                reader.join()
            Path(self.capabilities["socket_path"]).unlink(missing_ok=True)
