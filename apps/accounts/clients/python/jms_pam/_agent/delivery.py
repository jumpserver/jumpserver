"""Credential projection and JSON/EnvironmentFile delivery."""

import json
import subprocess

from ..models import Credential
from .storage import atomic_write, secure_root, secure_target


def flatten_credential(credential: Credential):
    account, asset = credential.account, credential.asset
    return {
        "key": credential.key,
        "revision": credential.revision,
        "asset_id": asset.id,
        "asset": asset.name,
        "address": asset.address,
        "account_id": account.id,
        "account": account.name,
        "username": account.username,
        "secret_type": account.secret_type,
        "secret": account.secret,
    }


def render_environment(item):
    values = {
        "JMS_PAM_CREDENTIAL_KEY": item["key"],
        "JMS_PAM_CREDENTIAL_REVISION": item["revision"],
        "JMS_PAM_ASSET_ID": item["asset_id"],
        "JMS_PAM_ASSET_ADDRESS": item["address"],
        "JMS_PAM_ACCOUNT_ID": item["account_id"],
        "JMS_PAM_USERNAME": item["username"],
        "JMS_PAM_SECRET_TYPE": item["secret_type"],
        "JMS_PAM_SECRET": item["secret"],
    }
    lines = []
    for name, value in values.items():
        value = str(value)
        if any(char in value for char in ("\x00", "\r", "\n")):
            raise ValueError("EnvironmentFile values cannot contain NUL or newlines.")
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("`", "\\`")
            .replace("$", "\\$")
        )
        lines.append(f'{name}="{escaped}"')
    return "\n".join(lines) + "\n"


def deliver_credentials(items, configuration):
    """Write a stable snapshot; the caller records delivery only after this returns."""
    mode = configuration["delivery_mode"]
    if mode == "socket":
        return
    root = secure_root(configuration["delivery_root"])
    owner = configuration["app_user"]
    suffix = "json" if mode == "json" else "env"
    for key, item in items.items():
        target = secure_target(root, f"{key}.{suffix}")
        content = (
            json.dumps(item, ensure_ascii=False, indent=2) + "\n"
            if mode == "json"
            else render_environment(item)
        )
        atomic_write(target, content, owner=owner)
    if mode == "environment":
        subprocess.run(
            [
                "systemctl",
                configuration["systemd_action"],
                configuration["systemd_unit"],
            ],
            check=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
