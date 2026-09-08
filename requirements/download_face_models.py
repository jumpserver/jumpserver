#!/usr/bin/env python3
"""Download the model files required by the JumpServer XPack face plugin."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

MODEL_NAME = "buffalo_l"
MODEL_URL = (
    "https://github.com/deepinsightface/insightface/releases/download/"
    "v0.7/buffalo_l.zip"
)
MODEL_SHA256 = "80ffe37d8a5940d59a7384c201a2a38d4741f2f3c51eef46ebb28218a7b0ca2f"
REQUIRED_FILES = (
    "1k3d68.onnx",
    "2d106det.onnx",
    "det_10g.onnx",
    "w600k_r50.onnx",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and verify the InsightFace buffalo_l model package."
    )
    parser.add_argument(
        "--model-root",
        default=os.environ.get("INSIGHTFACE_MODEL_ROOT", "~/.insightface/models"),
        help="Value used for INSIGHTFACE_MODEL_ROOT (default: %(default)s)",
    )
    parser.add_argument(
        "--archive",
        type=Path,
        help="Use an existing buffalo_l.zip instead of downloading it",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify whether all required model files are installed",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Verify and reinstall files even when the model is already complete",
    )
    return parser.parse_args()


def model_directory(model_root: Path) -> Path:
    root = model_root.expanduser().resolve()
    if root.name == "models":
        return root / MODEL_NAME
    return root / "models" / MODEL_NAME


def missing_files(model_dir: Path) -> tuple[str, ...]:
    return tuple(
        name
        for name in REQUIRED_FILES
        if not (model_dir / name).is_file() or (model_dir / name).stat().st_size == 0
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_archive(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    request = urllib.request.Request(
        MODEL_URL,
        headers={"User-Agent": "JumpServer-FaceModel-Downloader/1.0"},
    )
    print(f"Downloading {MODEL_URL}")
    try:
        with (
            urllib.request.urlopen(request, timeout=60) as response,
            temporary.open("wb") as output,
        ):
            total = int(response.headers.get("Content-Length") or 0)
            downloaded = 0
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                downloaded += len(chunk)
                if total:
                    print(
                        f"\rDownloaded {downloaded * 100 / total:5.1f}%",
                        end="",
                        flush=True,
                    )
        if total:
            print()
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def verify_archive(archive: Path) -> None:
    actual = file_sha256(archive)
    if actual != MODEL_SHA256:
        raise ValueError(
            f"Checksum mismatch for {archive}: expected {MODEL_SHA256}, got {actual}"
        )


def install_archive(archive: Path, model_dir: Path) -> None:
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as package:
        members = {item.filename: item for item in package.infolist()}
        absent = [name for name in REQUIRED_FILES if name not in members]
        if absent:
            raise ValueError(f"Model archive is missing: {', '.join(absent)}")
        with tempfile.TemporaryDirectory(
            prefix=f".{MODEL_NAME}-", dir=model_dir.parent
        ) as temporary:
            temporary_dir = Path(temporary)
            for name in REQUIRED_FILES:
                member = members[name]
                if member.is_dir() or Path(member.filename).name != member.filename:
                    raise ValueError(f"Unsafe model archive member: {member.filename}")
                target = temporary_dir / name
                with package.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                if target.stat().st_size == 0:
                    raise ValueError(f"Extracted model file is empty: {name}")
            model_dir.mkdir(parents=True, exist_ok=True)
            for name in REQUIRED_FILES:
                os.replace(temporary_dir / name, model_dir / name)


def run(args: argparse.Namespace) -> int:
    root = Path(args.model_root).expanduser().resolve()
    model_dir = model_directory(root)
    missing = missing_files(model_dir)
    if args.check:
        if missing:
            print(f"Model is incomplete at {model_dir}: {', '.join(missing)}")
            return 1
        print(f"Model is complete: {model_dir}")
        return 0
    if not missing and not args.force:
        print(f"Model is already complete: {model_dir}")
        return 0

    supplied_archive = args.archive is not None
    archive = (
        args.archive.expanduser().resolve()
        if supplied_archive
        else root / f"{MODEL_NAME}.zip"
    )
    if supplied_archive and not archive.is_file():
        raise ValueError(f"Model archive does not exist: {archive}")
    if not supplied_archive and (not archive.is_file() or args.force):
        download_archive(archive)
    print(f"Verifying SHA-256: {archive}")
    try:
        verify_archive(archive)
    except Exception:
        if not supplied_archive:
            archive.unlink(missing_ok=True)
        raise

    print(f"Installing {', '.join(REQUIRED_FILES)} into {model_dir}")
    install_archive(archive, model_dir)
    remaining = missing_files(model_dir)
    if remaining:
        raise RuntimeError(f"Model installation is incomplete: {', '.join(remaining)}")
    print(f"Face model installation complete: {model_dir}")
    print(
        "License notice: confirm that the InsightFace pretrained model license "
        "permits your intended deployment."
    )
    return 0


def main() -> int:
    try:
        return run(parse_args())
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
