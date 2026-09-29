"""Bootstrap registration and systemd installation, separate from the running Agent."""

import pwd
import shlex
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import requests

from .._version import CONFIG_SCHEMA_VERSION, PROTOCOL_VERSION, __version__
from ..client import CLIENT_PATH, Client
from .config import validate_configuration
from .runtime import Agent
from .storage import atomic_write, atomic_write_json, read_json, secure_root


def register(args):
    bootstrap = read_json(args.bootstrap) if getattr(args, "bootstrap", "") else None
    if bootstrap is not None:
        for name in ("endpoint", "configuration_id", "app_user", "install_path"):
            if not bootstrap.get(name):
                raise ValueError(f"Missing Agent bootstrap field: {name}")
            setattr(args, name, bootstrap[name])
        for name in ("app_id", "app_secret", "org_id"):
            if not bootstrap.get(name):
                raise ValueError(f"Missing Agent bootstrap field: {name}")
    elif not all(
        getattr(args, name, None)
        for name in (
            "endpoint",
            "token",
            "configuration_id",
            "app_user",
            "install_path",
        )
    ):
        raise ValueError("Use --bootstrap from the application access wizard.")
    configuration_id = str(uuid.UUID(args.configuration_id))
    base = Path(args.install_path) / configuration_id
    secure_root(base, 0o700)
    config_file = args.config or str(base / "agent.json")
    if Path(config_file).is_symlink():
        raise ValueError("Agent configuration cannot be a symbolic link.")
    config_path = Path(config_file).resolve(strict=False)
    if not config_path.is_relative_to(base.resolve()) or config_path == base.resolve():
        raise ValueError(
            "Agent configuration must remain inside its installation directory."
        )
    config_file = str(config_path)
    existing = read_json(config_file)
    if existing:
        if bootstrap is not None and existing.get("app_id") != bootstrap["app_id"]:
            raise ValueError(
                "Existing Agent belongs to another identity. Use a separate installation path."
            )
        agent = Agent(config_file)
        try:
            agent.sync()
        finally:
            agent.remote.close()
        print("Existing Agent identity verified and reused.")
        return config_file

    pwd.getpwnam(args.app_user)
    if bootstrap is not None:
        remote = Client(
            args.endpoint,
            app_id=bootstrap["app_id"],
            app_secret=bootstrap["app_secret"],
            instance_id=args.instance_id,
            org_id=bootstrap["org_id"],
            configuration_id=configuration_id,
            source="jms-pam-agent",
        )
        try:
            result = remote.sync_agent(
                credentials=[], delivered_credentials=[], config_digest=""
            )
        finally:
            remote.close()
        identity = {
            "configuration_id": configuration_id,
            "org_id": bootstrap["org_id"],
            "configuration": result.configuration,
            "config_digest": result.config_digest,
        }
    else:
        identity = register_legacy(args)
    configuration = identity["configuration"]
    if identity["configuration_id"] != configuration_id:
        raise ValueError("Registration belongs to another subscription scope.")
    if configuration["app_user"] != args.app_user:
        raise ValueError("Application user does not match the server configuration.")
    expected_root = str(Path(args.install_path) / "credentials" / configuration_id)
    if configuration["delivery_root"] != expected_root:
        raise ValueError("Install path does not match the server configuration.")
    capabilities = {
        key: configuration.get(key, "")
        for key in (
            "delivery_root",
            "socket_path",
            "app_user",
            "systemd_unit",
            "systemd_action",
        )
    }
    validate_configuration(configuration, capabilities)
    secure_root(configuration["delivery_root"])
    config = {
        "endpoint": args.endpoint.rstrip("/"),
        "org_id": identity["org_id"],
        "configuration_id": identity["configuration_id"],
        "instance_id": args.instance_id,
        "configuration": configuration,
        "capabilities": capabilities,
        "config_digest": identity["config_digest"],
        "authorized_keys": configuration["credential_keys"],
        "credential_file": str(base / "credentials.json"),
        "delivery_file": str(base / "delivered.json"),
        "state_file": str(base / "state.json"),
        "reconcile_interval": 300,
        "sync_status": "",
        "sync_error": "",
        "access_denied": False,
    }
    if bootstrap is not None:
        config.update(app_id=bootstrap["app_id"], app_secret=bootstrap["app_secret"])
    else:
        config.update(
            agent_id=identity["agent_id"], agent_secret=identity["agent_secret"]
        )
    atomic_write_json(config_file, config)
    atomic_write_json(config["credential_file"], {})
    atomic_write_json(config["delivery_file"], {})
    atomic_write_json(config["state_file"], {})
    return config_file


def register_legacy(args):
    response = requests.post(
        f"{args.endpoint.rstrip('/')}{CLIENT_PATH}/register-agent/",
        json={
            "token": args.token,
            "instance_id": args.instance_id,
            "name": args.name or args.instance_id,
            "client_version": __version__,
            "protocol_version": PROTOCOL_VERSION,
            "config_schema_version": CONFIG_SCHEMA_VERSION,
        },
        timeout=10,
    )
    try:
        response.raise_for_status()
        identity = response.json()
    except (requests.RequestException, ValueError) as error:
        raise RuntimeError(
            "Agent registration failed; the local configuration was not replaced."
        ) from error
    return identity


def install(args):
    config_file = register(args)
    executable = shutil.which("jms-pam-agent")
    command = [executable] if executable else [sys.executable, "-m", "jms_pam.agent"]
    command.extend(("run", "--config", config_file))
    service = f"jms-pam-agent-{uuid.UUID(args.configuration_id)}.service"
    unit_path = Path("/etc/systemd/system") / service
    unit = (
        "[Unit]\nDescription=JumpServer PAM Agent\nAfter=network-online.target\n\n"
        "[Service]\nType=simple\nUser=root\n"
        f"ExecStart={' '.join(shlex.quote(value) for value in command)}\n"
        "Restart=always\nRestartSec=5\n\n"
        "[Install]\nWantedBy=multi-user.target\n"
    )
    atomic_write(unit_path, unit, mode=0o644)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", service], check=True)
    subprocess.run(["systemctl", "is-active", "--quiet", service], check=True)
