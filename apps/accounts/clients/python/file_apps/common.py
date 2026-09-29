import argparse
import importlib.util
import json
import os
import tempfile
from pathlib import Path


def arguments(description, rotation=False):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--config", required=True, type=Path, help="Generated jms_pam_config.py"
    )
    parser.add_argument(
        "--instance-id",
        required=True,
        help="Stable, unique ID for this application replica",
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="Local JSON configuration file"
    )
    if rotation:
        parser.add_argument(
            "--confirm-file-only",
            action="store_true",
            help="Demo only: confirm a rotation after writing and reading back the local file",
        )
    return parser.parse_args()


def load_sdk_config(path):
    path = path.expanduser().resolve(strict=True)
    spec = importlib.util.spec_from_file_location("jms_pam_demo_config", path)
    if not spec or not spec.loader:
        raise ValueError("Cannot load the generated SDK configuration")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_local(path, kind):
    path = path.expanduser()
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except FileNotFoundError:
        return {"kind": kind, "credentials": {}}
    if data.get("kind") != kind or not isinstance(data.get("credentials"), dict):
        raise ValueError("The local configuration has an unexpected format")
    return data


def save_local(path, data):
    """Replace the whole secret-bearing file, never expose a partial write."""
    path = path.expanduser().absolute()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), 0o600)
            json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def credential_data(response):
    return {
        "key": response.key,
        "revision": response.revision,
        "asset": {
            "id": response.asset.id,
            "name": response.asset.name,
            "address": response.asset.address,
        },
        "account": {
            "id": response.account.id,
            "name": response.account.name,
            "username": response.account.username,
            "secret_type": response.account.secret_type,
            "secret": response.account.secret,
        },
    }


def verify_local(path, kind, selector, response):
    stored = load_local(path, kind)["credentials"][selector]
    if (
        stored["revision"] != response.revision
        or stored["account"]["id"] != response.account.id
        or stored["account"]["secret"] != response.account.secret
    ):
        raise RuntimeError(
            "The local configuration did not retain the fetched credential"
        )
