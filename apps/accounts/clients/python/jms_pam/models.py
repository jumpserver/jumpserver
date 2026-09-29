"""Typed responses using the same field names as the HTTP API."""

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


def _required(data: dict[str, Any], *names: str) -> None:
    if not isinstance(data, dict):
        raise TypeError("Response body must be a JSON object")
    missing = [name for name in names if data.get(name) in (None, "")]
    if missing:
        raise ValueError(f"{', '.join(missing)} is required")


def _string(data, name):
    _required(data, name)
    value = data[name]
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _revision(data):
    _required(data, "revision")
    value = data["revision"]
    if type(value) is not int or value < 0:
        raise ValueError("revision must be a non-negative integer")
    return value


def _boolean(data, name):
    _required(data, name)
    value = data[name]
    if type(value) is not bool:
        raise TypeError(f"{name} must be a boolean")
    return value


@dataclass(frozen=True)
class Platform:
    id: str
    name: str
    category: str
    type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Platform":
        return cls(
            id=_string(data, "id"),
            name=_string(data, "name"),
            category=_string(data, "category"),
            type=_string(data, "type"),
        )


@dataclass(frozen=True)
class Asset:
    id: str
    name: str
    address: str
    platform: Platform

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Asset":
        _required(data, "id", "name", "address", "platform")
        return cls(
            _string(data, "id"),
            _string(data, "name"),
            _string(data, "address"),
            Platform.from_dict(data["platform"]),
        )


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    username: str
    secret_type: str
    secret: str = field(repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Account":
        _required(data, "id", "name", "username", "secret_type", "secret")
        return cls(
            id=_string(data, "id"),
            name=_string(data, "name"),
            username=_string(data, "username"),
            secret_type=_string(data, "secret_type"),
            secret=_string(data, "secret"),
        )


@dataclass(frozen=True)
class Credential:
    key: str
    revision: int
    asset: Asset
    account: Account

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Credential":
        _required(data, "key", "revision", "asset", "account")
        return cls(
            _string(data, "key"),
            _revision(data),
            Asset.from_dict(data["asset"]),
            Account.from_dict(data["account"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return delivery data, including the secret; never log this mapping."""
        return asdict(self)


@dataclass(frozen=True)
class CredentialConfirmation:
    key: str
    revision: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CredentialConfirmation":
        _required(data, "key", "revision")
        return cls(_string(data, "key"), _revision(data))


@dataclass(frozen=True)
class KnownRevision:
    key: str
    revision: int

    def __post_init__(self):
        if (
            not isinstance(self.key, str)
            or not self.key
            or type(self.revision) is not int
            or self.revision < 0
        ):
            raise ValueError("A key and a non-negative integer revision are required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CredentialRevision:
    key: str
    revision: int
    available: bool
    changed: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CredentialRevision":
        _required(data, "key", "revision", "available", "changed")
        return cls(
            key=_string(data, "key"),
            revision=_revision(data),
            available=_boolean(data, "available"),
            changed=_boolean(data, "changed"),
        )


@dataclass(frozen=True)
class AgentSync:
    config_digest: str
    credentials: list[CredentialRevision]
    removed_keys: list[str]
    date_last_synced: str
    configuration: Optional[dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentSync":
        _required(
            data, "config_digest", "credentials", "removed_keys", "date_last_synced"
        )
        if not isinstance(data["credentials"], list) or not isinstance(
            data["removed_keys"], list
        ):
            raise TypeError("Credential revisions and removed keys must be lists")
        if not all(isinstance(key, str) and key for key in data["removed_keys"]):
            raise TypeError("Removed keys must be non-empty strings")
        configuration = data.get("configuration")
        if configuration is not None and not isinstance(configuration, dict):
            raise TypeError("Agent configuration must be an object")
        credentials = [
            CredentialRevision.from_dict(item) for item in data["credentials"]
        ]
        if len({item.key for item in credentials}) != len(credentials):
            raise ValueError("Credential revision keys must be unique")
        return cls(
            _string(data, "config_digest"),
            credentials,
            list(data["removed_keys"]),
            _string(data, "date_last_synced"),
            configuration,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommandResult:
    accepted: bool
    status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommandResult":
        _required(data, "accepted", "status")
        return cls(_boolean(data, "accepted"), _string(data, "status"))
