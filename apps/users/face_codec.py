from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FaceCodecAdapter:
    is_native_code: Callable[[str | None], bool]
    compare_codes: Callable[..., bool]
    decode_code: Callable[[str], list[float]]


_adapter: FaceCodecAdapter | None = None


def register_face_codec(
    *,
    is_native_code: Callable[[str | None], bool],
    compare_codes: Callable[..., bool],
    decode_code: Callable[[str], list[float]],
) -> None:
    global _adapter
    _adapter = FaceCodecAdapter(
        is_native_code=is_native_code,
        compare_codes=compare_codes,
        decode_code=decode_code,
    )


def get_face_codec() -> FaceCodecAdapter | None:
    return _adapter
