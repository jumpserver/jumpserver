"""Run SDKs against one shared HTTP/WebSocket signature contract fixture."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

CLIENTS = Path(__file__).resolve().parents[1]


def main():
    maven = os.environ.get("JMS_MAVEN") or shutil.which("mvn")
    if not maven:
        raise SystemExit("Set JMS_MAVEN to Maven 3.9+, or install Maven on PATH.")
    fixture = subprocess.Popen(
        ["node", str(CLIENTS / "tests" / "contract-server.js")],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        endpoint = fixture.stdout.readline().strip()
        if not endpoint.startswith("http://127.0.0.1:"):
            raise RuntimeError("Protocol fixture did not start")
        environment = {**os.environ, "JMS_TEST_ENDPOINT": endpoint}
        subprocess.run(
            [sys.executable, str(CLIENTS / "tests" / "test_python_contract.py")],
            env=environment,
            check=True,
        )
        subprocess.run(
            ["go", "test", "-race", "./..."],
            cwd=CLIENTS / "go",
            env=environment,
            check=True,
        )
        subprocess.run(
            [maven, "-q", "test"], cwd=CLIENTS / "java", env=environment, check=True
        )
        subprocess.run(
            ["npm", "test"], cwd=CLIENTS / "node", env=environment, check=True
        )
        # The server also verifies signature order, exact digest bytes and fresh request IDs.
        import json
        import urllib.request

        stats = json.load(
            urllib.request.urlopen(endpoint.removesuffix("/prefix") + "/__stats")
        )
        if stats["failures"]:
            raise AssertionError(stats["failures"])
        print("All native SDK protocol contracts passed.")
    finally:
        fixture.terminate()
        try:
            fixture.wait(timeout=5)
        except subprocess.TimeoutExpired:
            fixture.kill()
            fixture.wait()


if __name__ == "__main__":
    main()
