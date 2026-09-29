"""HTTP signature authentication shared by HTTP and WebSocket requests."""

import base64
import hashlib
import hmac
import uuid
from email.utils import formatdate

from requests.auth import AuthBase

SIGNATURE_HEADERS = (
    "(request-target)",
    "accept",
    "date",
    "digest",
    "x-jms-request-id",
    "x-jms-org",
    "x-jms-client-version",
    "x-jms-protocol-version",
    "x-jms-config-schema-version",
)


class HTTPSignatureAuth(AuthBase):
    def __init__(self, key_id, secret):
        self.key_id = key_id
        self.secret = secret.encode("ascii")

    def __call__(self, request):
        body = request.body or b""
        if isinstance(body, str):
            body = body.encode()
        if not isinstance(body, bytes):
            raise TypeError("Signed request bodies must be bytes or strings.")
        request.headers["Digest"] = "SHA-256=" + base64.b64encode(
            hashlib.sha256(body).digest()
        ).decode("ascii")
        request.headers.setdefault("Date", formatdate(usegmt=True))
        request.headers.setdefault("X-JMS-Request-ID", str(uuid.uuid4()))
        values = []
        for header in SIGNATURE_HEADERS:
            value = (
                f"{request.method.lower()} {request.path_url}"
                if header == "(request-target)"
                else request.headers[header]
            )
            values.append(f"{header}: {value}")
        digest = base64.b64encode(
            hmac.new(
                self.secret,
                "\n".join(values).encode("ascii"),
                hashlib.sha256,
            ).digest()
        ).decode("ascii")
        request.headers["Authorization"] = (
            f'Signature keyId="{self.key_id}",algorithm="hmac-sha256",'
            f'signature="{digest}",headers="{" ".join(SIGNATURE_HEADERS)}"'
        )
        return request
