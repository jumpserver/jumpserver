"""Compatibility imports for the original SDK exception module."""

from ..exceptions import (
    REVOKED_CODES,
    PAMError,
    identity_denied,
    response_error_code,
)

JumpServerPAMSDKException = PAMError

__all__ = [
    "JumpServerPAMSDKException",
    "REVOKED_CODES",
    "identity_denied",
    "response_error_code",
]
