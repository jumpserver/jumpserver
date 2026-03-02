import os
from collections import defaultdict
from functools import reduce

from django.conf import settings


class DefaultCallback:
    STATUS_MAPPER = {
        "successful": "success",
        "failure": "failed",
        "failed": "failed",
        "running": "running",
        "pending": "pending",
        "timeout": "timeout",
        "unknown": "unknown",
    }

    def __init__(self):
        self.result = dict(
            ok=defaultdict(dict),
            failures=defaultdict(dict),
            dark=defaultdict(dict),
            skipped=defaultdict(dict),
            ignored=defaultdict(dict),
        )
        self.summary = dict(
            ok=[],
            failures={},
            dark={},
            skipped=[],
        )
        self.status = "running"
        self.finished = False
        self.local_pid = 0
        self.private_data_dir = None

    @property
    def host_results(self):
        results = defaultdict(dict)
        for state, hosts in self.result.items():
            for host, items in hosts.items():
                results[host][state] = items
        return results

    def is_success(self):
        return self.status != "success"

    def event_handler(self, data, **kwargs):
        event = data.get("event", None)
        if not event:
            return

        pid = data.get("pid", None)
        if pid:
            self.write_pid(pid)

        event_data = data.get("event_data", {})
        host = event_data.get("remote_addr", "")
        task = event_data.get("task", "")
        res = event_data.get("res", {})
        handler = getattr(self, event, self.on_any)
        handler(event_data, host=host, task=task, res=res)

    def runner_on_ok(self, event_data, host=None, task=None, res=None):
        detail = {
            "action": event_data.get("task_action", ""),
            "res": res,
            "rc": res.get("rc", 0),
            "stdout": res.get("stdout", ""),
        }
        self.result["ok"][host][task] = detail

    def runner_on_skipped(self, event_data, host=None, task=None, **kwargs):
        detail = {
            "action": event_data.get("task_action", ""),
            "res": {},
            "rc": 0,
        }
        self.result["skipped"][host][task] = detail

    def runner_on_failed(self, event_data, host=None, task=None, res=None, **kwargs):
        detail = {
            "action": event_data.get("task_action", ""),
            "res": res,
            "rc": res.get("rc", 0),
            "stdout": res.get("stdout", ""),
            "stderr": ";".join([res.get("stderr", ""), res.get("msg", "")]).strip(";"),
        }
        ignore_errors = event_data.get("ignore_errors", False)
        error_key = "ignored" if ignore_errors else "failures"
        self.result[error_key][host][task] = detail

    def runner_on_unreachable(
            self, event_data, host=None, task=None, res=None, **kwargs
    ):
        detail = {
            "action": event_data.get("task_action", ""),
            "res": res,
            "rc": 255,
            "stderr": ";".join([res.get("stderr", ""), res.get("msg", "")]).strip(";"),
        }
        ignore_unreachable = event_data.get("ignore_unreachable", False)
        if not ignore_unreachable:
            ignore_unreachable = self._task_path_ignores_unreachable(
                event_data.get("task_path", "")
            )
        error_key = "ignored" if ignore_unreachable else "dark"
        self.result[error_key][host][task] = detail

    @staticmethod
    def _task_path_ignores_unreachable(task_path):
        if not task_path or ":" not in task_path:
            return False

        path, line_str = task_path.rsplit(":", 1)
        try:
            line_no = int(line_str)
        except ValueError:
            return False

        try:
            with open(path, "r") as f:
                lines = f.readlines()
        except OSError:
            return False

        line_no = max(1, min(line_no, len(lines)))

        def is_task_start(line):
            stripped = line.lstrip(" \t")
            return stripped.startswith("- ")

        start_idx = None
        start_indent = 0
        for idx in range(line_no - 1, -1, -1):
            if is_task_start(lines[idx]):
                start_idx = idx
                start_indent = len(lines[idx]) - len(lines[idx].lstrip(" \t"))
                break

        if start_idx is None:
            return False

        for line in lines[start_idx + 1:]:
            stripped = line.lstrip(" \t")
            if stripped.startswith("- "):
                curr_indent = len(line) - len(stripped)
                if curr_indent <= start_indent:
                    break
            if "ignore_unreachable:" in line:
                return True

        return False

    def runner_on_start(self, event_data, **kwargs):
        pass

    def runner_retry(self, event_data, **kwargs):
        pass

    def runner_on_file_diff(self, event_data, **kwargs):
        pass

    def runner_item_on_failed(self, event_data, **kwargs):
        pass

    def runner_item_on_skipped(self, event_data, **kwargs):
        pass

    def playbook_on_play_start(self, event_data, **kwargs):
        pass

    def playbook_on_stats(self, event_data, **kwargs):
        error_func = (
            lambda err, task_detail: err
                                     + f"{task_detail[0]}: {task_detail[1]['stderr']};"
        )
        for tp in ["dark", "failures"]:
            for host, tasks in self.result[tp].items():
                error = reduce(error_func, tasks.items(), "").strip(";")
                self.summary[tp][host] = error
        failures = list(self.result["failures"].keys())
        dark_or_failures = list(self.result["dark"].keys()) + failures

        for host, tasks in self.result.get("ignored", {}).items():
            ignore_errors = reduce(error_func, tasks.items(), "").strip(";")
            if host in failures:
                self.summary["failures"][host] += ignore_errors

        self.summary["ok"] = list(set(self.result["ok"].keys()) - set(dark_or_failures))
        self.summary["skipped"] = list(
            set(self.result["skipped"].keys()) - set(dark_or_failures)
        )

    def playbook_on_include(self, event_data, **kwargs):
        pass

    def playbook_on_notify(self, event_data, **kwargs):
        pass

    def playbook_on_vars_prompt(self, event_data, **kwargs):
        pass

    def playbook_on_handler_task_start(self, event_data, **kwargs):
        pass

    def playbook_on_no_hosts_matched(self, event_data, **kwargs):
        pass

    def playbook_on_no_hosts_remaining(self, event_data, **kwargs):
        pass

    def playbook_on_start(self, event_data, **kwargs):
        if settings.DEBUG_DEV:
            print("DEBUG: delete inventory: ", os.path.join(self.private_data_dir, 'inventory'))
        inventory_path = os.path.join(self.private_data_dir, 'inventory', 'hosts')
        if os.path.exists(inventory_path):
            os.remove(inventory_path)

    def warning(self, event_data, **kwargs):
        pass

    def on_any(self, event_data, **kwargs):
        pass

    def status_handler(self, data, **kwargs):
        status = data.get("status", "")
        self.status = self.STATUS_MAPPER.get(status, "unknown")
        self.private_data_dir = data.get("private_data_dir", None)

    def write_pid(self, pid):
        pid_filepath = os.path.join(self.private_data_dir, "local.pid")
        with open(pid_filepath, "w") as f:
            f.write(str(pid))
