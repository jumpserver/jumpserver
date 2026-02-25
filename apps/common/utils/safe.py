import logging
import subprocess

logger = logging.getLogger(__name__)


def safe_run_cmd(cmd_args, shell=False):
    if shell:
        raise ValueError("shell=True is not allowed in safe_run_cmd. " "Pass command as a list with shell=False.")
    cmd_args = [str(arg) for arg in cmd_args]
    try:
        return subprocess.run(cmd_args, shell=False)
    except Exception as e:
        logger.error("Failed to run command %s: %s", cmd_args, e)
        return None


def truncate_file(file_path):
    try:
        with open(file_path, "w"):
            pass
    except Exception as e:
        logger.error("Failed to truncate file %s: %s", file_path, e)


def find_and_delete_files(directory, name_pattern=None, mtime_days=None):
    cmd = ["find", str(directory), "-type", "f"]
    if mtime_days is not None:
        cmd.extend(["-mtime", "+%s" % int(mtime_days)])
    if name_pattern is not None:
        cmd.extend(["-name", str(name_pattern)])
    cmd.append("-delete")
    return safe_run_cmd(cmd)


def find_and_delete_empty_dirs(directory):
    cmd = ["find", str(directory), "-type", "d", "-empty", "-delete"]
    return safe_run_cmd(cmd)
