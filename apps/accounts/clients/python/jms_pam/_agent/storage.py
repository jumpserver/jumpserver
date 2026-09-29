"""Private state and capability-constrained filesystem operations."""

import json
import os
import pwd
import tempfile
from pathlib import Path


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        return {} if default is None else default


def atomic_write(path, content, mode=0o600, owner=None):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError("Target path cannot be a symbolic link.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            delete=False,
        ) as stream:
            temporary = stream.name
            os.fchmod(stream.fileno(), mode)
            if owner:
                user = pwd.getpwnam(owner)
                os.fchown(stream.fileno(), user.pw_uid, user.pw_gid)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if target.is_symlink():
            raise ValueError("Target path cannot be a symbolic link.")
        os.replace(temporary, target)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_json(path, data, mode=0o600, owner=None):
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    atomic_write(path, content, mode=mode, owner=owner)


def secure_root(path, mode=0o711):
    target = Path(path)
    if not target.is_absolute() or target == Path("/"):
        raise ValueError(
            "Agent paths must be absolute and cannot be the filesystem root."
        )
    for item in (target, *target.parents):
        if item.is_symlink():
            raise ValueError("Agent paths cannot contain symbolic links.")
    target.mkdir(parents=True, exist_ok=True)
    info = target.stat()
    if info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError(
            "Agent output directories must be root-owned and not writable by group or others."
        )
    os.chmod(target, mode)
    return target.resolve()


def secure_target(root, name):
    root = Path(root).resolve()
    if not isinstance(name, str) or Path(name).name != name:
        raise ValueError(
            "Credential delivery filenames cannot contain path separators."
        )
    target = root / name
    if target.is_symlink():
        raise ValueError("Credential delivery paths cannot contain symbolic links.")
    target = target.resolve(strict=False)
    if not target.is_relative_to(root) or target == root:
        raise ValueError("Credential delivery escaped its configured root.")
    for item in (target, *target.parents):
        if item == root.parent:
            break
        if item.exists() and item.is_symlink():
            raise ValueError("Credential delivery paths cannot contain symbolic links.")
    return target
