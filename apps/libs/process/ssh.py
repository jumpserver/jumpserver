import logging

import psutil
from psutil import NoSuchProcess

logger = logging.getLogger(__name__)


def _should_kill(process):
    return process.pid != 1 and process.name() == 'ssh'


def kill_ansible_ssh_process(pid):
    try:
        process = psutil.Process(pid)
    except NoSuchProcess as e:
        logger.error(f"No such process: {e}")
        return

    for child in process.children(recursive=True):
        if not _should_kill(child):
            return
        try:
            child.kill()
        except Exception as e:
            logger.error(f"Failed to kill process {child.pid}: {e}")
