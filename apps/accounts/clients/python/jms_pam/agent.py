"""Command line entry point and public Agent import."""

import argparse
import json
import signal
import socket
import threading

from ._agent.config import CONFIG_FILE
from ._agent.install import install, register
from ._agent.runtime import Agent
from ._agent.storage import read_json

__all__ = ["Agent", "build_parser", "install", "main", "read_json", "register"]


def confirm_local(args):
    body = json.dumps({"key": args.key, "revision": args.revision}).encode()
    request = (
        b"POST /v1/confirm HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()
        + body
    )
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(15)
        client.connect(args.socket)
        client.sendall(request)
        response = b""
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            response += chunk
    status_line, _, payload = response.partition(b"\r\n\r\n")
    if b" 200 " not in status_line.split(b"\r\n", 1)[0]:
        raise RuntimeError(payload.decode(errors="replace"))
    print(payload.decode())


def run_agent(args):
    stop = threading.Event()
    previous = {}
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, lambda *_: stop.set())
    try:
        Agent(args.config).run(stop)
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def build_parser():
    parser = argparse.ArgumentParser(prog="jms-pam-agent")
    commands = parser.add_subparsers(dest="command", required=True)

    def add_registration_arguments(command):
        command.add_argument("--bootstrap", default="")
        command.add_argument("--endpoint")
        command.add_argument("--token")
        command.add_argument("--instance-id", required=True)
        command.add_argument("--configuration-id")
        command.add_argument("--app-user")
        command.add_argument("--install-path")
        command.add_argument("--name")
        command.add_argument("--config", default="")

    register_parser = commands.add_parser("register")
    add_registration_arguments(register_parser)
    register_parser.set_defaults(handler=register)

    install_parser = commands.add_parser("install")
    add_registration_arguments(install_parser)
    install_parser.set_defaults(handler=install)

    run_parser = commands.add_parser("run")
    run_parser.add_argument("--config", default=CONFIG_FILE)
    run_parser.set_defaults(handler=run_agent)

    confirm_parser = commands.add_parser("confirm")
    confirm_parser.add_argument("key")
    confirm_parser.add_argument("--revision", type=int, required=True)
    confirm_parser.add_argument("--socket", required=True)
    confirm_parser.set_defaults(handler=confirm_local)
    return parser


def main():
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
