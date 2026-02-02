import os
import stat
import hashlib
from pathlib import Path
from rest_framework.exceptions import ValidationError
from zipfile import ZipFile, BadZipFile


# -------------------------
# 可按你们安全规范调整
# -------------------------
MAX_FILES = 1000
MAX_SINGLE_FILE_SIZE = 200 * 1024 * 1024      # 200MB
MAX_TOTAL_SIZE = 1 * 1024 * 1024 * 1024        # 1GB
MAX_COMPRESSION_RATIO = 100                   # 解压 / 压缩


class ZipSecurityError(ValidationError):
    pass


# -------------------------
# 工具函数
# -------------------------
def _is_symlink(zip_info):
    return stat.S_ISLNK(zip_info.external_attr >> 16)


def _is_safe_path(base_dir: Path, target: Path) -> bool:
    try:
        return target.resolve().is_relative_to(base_dir.resolve())
    except AttributeError:
        # Python < 3.9
        return str(target.resolve()).startswith(str(base_dir.resolve()))


def _verify_signature(zip_path: Path, sig_path: Path, public_key_pem: bytes):
    """
    示例：RSA + SHA256
    你可以替换成你们自己的验签逻辑
    """
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    data = zip_path.read_bytes()
    signature = sig_path.read_bytes()

    public_key = serialization.load_pem_public_key(public_key_pem)

    public_key.verify(
        signature,
        data,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )


# -------------------------
# 主函数
# -------------------------
def safe_extract_zip(
    zip_path: str | Path,
    extract_dir: str | Path,
    zip_sign_path: str | Path | None = None,
    *,
    public_key_pem: bytes | None = None,
):
    """
    安全解压 zip

    :param zip_path: zip 文件路径
    :param extract_dir: 解压目标目录
    :param zip_sign_path: 可选，zip 签名文件路径
    :param public_key_pem: 可选，验签用公钥
    """

    zip_path = Path(zip_path)
    extract_dir = Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    # 1️⃣ 签名校验
    if zip_sign_path:
        if not public_key_pem:
            raise ZipSecurityError("Signature provided but public key missing")

        _verify_signature(
            zip_path,
            Path(zip_sign_path),
            public_key_pem,
        )

    try:
        with ZipFile(zip_path) as zf:
            infos = zf.infolist()

            # 2️⃣ 条目数量限制
            if len(infos) > MAX_FILES:
                raise ZipSecurityError("Too many files in zip")

            total_size = 0

            for info in infos:
                name = info.filename

                # 3️⃣ 基础文件名校验
                if name.startswith(("/", "\\")):
                    raise ZipSecurityError(f"Absolute path not allowed: {name}")

                if ".." in Path(name).parts:
                    raise ZipSecurityError(f"Path traversal detected: {name}")

                # 4️⃣ 软链接检测
                if _is_symlink(info):
                    raise ZipSecurityError(f"Symlink not allowed: {name}")

                # 5️⃣ 文件大小限制
                if info.file_size > MAX_SINGLE_FILE_SIZE:
                    raise ZipSecurityError(f"File too large: {name}")

                total_size += info.file_size
                if total_size > MAX_TOTAL_SIZE:
                    raise ZipSecurityError("Total extracted size exceeded")

                # 6️⃣ 压缩比校验（防 zip bomb）
                if info.compress_size > 0:
                    ratio = info.file_size / info.compress_size
                    if ratio > MAX_COMPRESSION_RATIO:
                        raise ZipSecurityError(
                            f"Suspicious compression ratio ({ratio:.1f}): {name}"
                        )

                # 7️⃣ 最终路径校验
                target_path = extract_dir / name
                if not _is_safe_path(extract_dir, target_path):
                    raise ZipSecurityError(f"Unsafe extract path: {name}")

                # 8️⃣ 解压（手动）
                if info.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as src, open(target_path, "wb") as dst:
                        dst.write(src.read())

    except BadZipFile:
        raise ZipSecurityError("Invalid zip file")