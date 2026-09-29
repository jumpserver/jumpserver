"""Local HTTP API over a protected Unix socket."""

import json
import os
import pwd
import socketserver
import stat
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

from .storage import secure_root


class ThreadingUnixHTTPServer(
    socketserver.ThreadingMixIn, socketserver.UnixStreamServer
):
    daemon_threads = False


def reply(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def start_local_server(agent):

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(10)
            super().setup()

        def do_GET(self):
            if self.path == "/v1/health":
                return reply(self, 200, agent.health())
            prefix = "/v1/credentials/"
            if not self.path.startswith(prefix):
                return reply(self, 404, {"code": "not_found"})
            key = unquote(self.path[len(prefix) :])
            try:
                item = agent.local_credential(key)
            except PermissionError as error:
                return reply(self, 503, {"code": str(error)})
            except KeyError as error:
                return reply(self, 404, {"code": error.args[0]})
            return reply(self, 200, item)

        def do_POST(self):
            if self.path != "/v1/confirm":
                return reply(self, 404, {"code": "not_found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("Invalid request size.")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict) or not isinstance(data.get("key"), str):
                    raise ValueError("Invalid confirmation body.")
                result = agent.confirm(data["key"], data["revision"])
                return reply(self, 200, result)
            except PermissionError as error:
                return reply(self, 503, {"code": str(error)})
            except OSError:
                return reply(self, 503, {"code": "agent_unavailable"})
            except Exception as error:
                return reply(self, 400, {"code": type(error).__name__})

        def log_message(self, *_):
            pass

    path = Path(agent.capabilities["socket_path"])
    parent = path.parent
    secure_root(parent, 0o750)
    if path.is_symlink():
        raise ValueError("Agent socket path cannot be a symbolic link.")
    if path.exists():
        if not stat.S_ISSOCK(path.stat().st_mode):
            raise ValueError("Agent socket path is occupied by a non-socket file.")
        path.unlink()
    user = pwd.getpwnam(agent.capabilities["app_user"])
    os.chown(parent, 0, user.pw_gid)
    os.chmod(parent, 0o750)
    server = ThreadingUnixHTTPServer(str(path), Handler)
    try:
        os.chown(path, user.pw_uid, user.pw_gid)
        os.chmod(path, 0o600)
        threading.Thread(
            target=server.serve_forever, name="jms-pam-local-api", daemon=True
        ).start()
    except Exception:
        server.server_close()
        path.unlink(missing_ok=True)
        raise
    return server
