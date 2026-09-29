"""HTTP session ownership and response decoding, independent of SDK operations."""

from threading import Lock
from typing import Any, Callable, TypeVar

import requests

from .exceptions import PAMError

Response = TypeVar("Response")


class Transport:
    """Serialize access to one reusable session, including its shutdown."""

    def __init__(self):
        self.session = requests.Session()
        self._lock = Lock()
        self._closed = False

    def request(
        self,
        method: str,
        url: str,
        parse: Callable[[dict[str, Any]], Response],
        **options: Any,
    ) -> Response:
        with self._lock:
            if self._closed:
                raise RuntimeError("Client is closed")
            try:
                response = self.session.request(method, url, **options)
            except requests.RequestException as error:
                raise PAMError(
                    "NetworkError", str(error), original_error=error
                ) from error
            try:
                return self._decode(response, parse)
            finally:
                response.close()

    @staticmethod
    def _decode(response, parse):
        try:
            payload = response.json()
        except (TypeError, ValueError) as error:
            raise PAMError(
                "ResponseError",
                "The server returned invalid JSON",
                status_code=response.status_code,
                original_error=error,
            ) from error
        if not isinstance(payload, dict):
            raise PAMError(
                "ResponseError",
                "The server response must be a JSON object",
                status_code=response.status_code,
            )
        if not 200 <= response.status_code < 300:
            error = requests.HTTPError(
                f"{response.status_code} {response.reason}", response=response
            )
            code = payload.get("code")
            detail = payload.get("detail")
            request_id = payload.get("request_id")
            code = code if isinstance(code, str) and code else "HTTPError"
            detail = detail if isinstance(detail, str) else None
            request_id = request_id if isinstance(request_id, str) else None
            raise PAMError(
                code,
                detail or response.reason or "HTTP request failed",
                status_code=response.status_code,
                detail=detail,
                request_id=request_id,
                original_error=error,
            ) from error
        try:
            return parse(payload)
        except (KeyError, TypeError, ValueError) as error:
            raise PAMError(
                "ResponseError",
                "The server returned an invalid response",
                status_code=response.status_code,
                original_error=error,
            ) from error

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                self.session.close()
