import re
import subprocess
import shlex


def safe_run_cmd(cmd_str, cmd_args=(), shell=True):
    cmd_args = [shlex.quote(arg) for arg in cmd_args]
    cmd = cmd_str % tuple(cmd_args)
    return subprocess.run(cmd, shell=shell)