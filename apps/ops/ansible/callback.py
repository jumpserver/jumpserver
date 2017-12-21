# ~*~ coding: utf-8 ~*~

from ansible.plugins.callback import CallbackBase
from ansible.plugins.callback.default import CallbackModule


class AdHocResultCallback(CallbackModule):
    """
    Task result Callback
    """
    def __init__(self, display=None, options=None):
        # result_raw example: {
        #   "ok": {"hostname": {"task_name": {}，...},..},
        #   "failed": {"hostname": {"task_name": {}..}, ..},
        #   "unreachable: {"hostname": {"task_name": {}, ..}},
        #   "skipped": {"hostname": {"task_name": {}, ..}, ..},
        # }
        # results_summary example: {
        #   "contacted": {"hostname",...},
        #   "dark": {"hostname": {"task_name": {}, "task_name": {}},...,},
        # }
        self.results_raw = dict(ok={}, failed={}, unreachable={}, skipped={})
        self.results_summary = dict(contacted=[], dark={})
        super().__init__()

    def gather_result(self, t, res):
        self._clean_results(res._result, res._task.action)
        host = res._host.get_name()
        task_name = res.task_name
        task_result = res._result

        if self.results_raw[t].get(host):
            self.results_raw[t][host][task_name] = task_result
        else:
            self.results_raw[t][host] = {task_name: task_result}
        self.clean_result(t, host, task_name, task_result)

    def clean_result(self, t, host, task_name, task_result):
        contacted = self.results_summary["contacted"]
        dark = self.results_summary["dark"]
        if t in ("ok", "skipped") and host not in dark:
            if host not in contacted:
                contacted.append(host)
        else:
            if dark.get(host):
                dark[host][task_name] = task_result.values
            else:
                dark[host] = {task_name: task_result}
            if host in contacted:
                contacted.remove(host)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.gather_result("failed", result)
        super().v2_runner_on_failed(result, ignore_errors=ignore_errors)

    def v2_runner_on_ok(self, result):
        self.gather_result("ok", result)
        super().v2_runner_on_ok(result)

    def v2_runner_on_skipped(self, result):
        self.gather_result("skipped", result)
        super().v2_runner_on_skipped(result)

    def v2_runner_on_unreachable(self, result):
        self.gather_result("unreachable", result)
        super().v2_runner_on_unreachable(result)


class CommandResultCallback(AdHocResultCallback):
    """
    Command result callback
    """
    def __init__(self, display=None):
        # results_command: {
        #   "cmd": "",
        #   "stderr": "",
        #   "stdout": "",
        #   "rc": 0,
        #   "delta": 0:0:0.123
        # }
        #
        self.results_command = dict()
        super().__init__(display)

    def gather_result(self, t, res):
        super().gather_result(t, res)
        self.gather_cmd(t, res)

    def gather_cmd(self, t, res):
        host = res._host.get_name()
        cmd = {}
        if t == "ok":
            cmd['cmd'] = res._result.get('cmd')
            cmd['stderr'] = res._result.get('stderr')
            cmd['stdout'] = res._result.get('stdout')
            cmd['rc'] = res._result.get('rc')
            cmd['delta'] = res._result.get('delta')
        else:
            cmd['err'] = "Error: {}".format(res)
        self.results_command[host] = cmd


class PlaybookResultCallBack(CallbackBase):
    """
    Custom callback model for handlering the output data of
    execute playbook file,
    Base on the build-in callback plugins of ansible which named `json`.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'Dict'

    def __init__(self, display=None):
        super(PlaybookResultCallBack, self).__init__(display)
        self.results = []
        self.output = ""
        self.item_results = {}  # {"host": []}

    def _new_play(self, play):
        return {
            'play': {
                'name': play.name,
                'id': str(play._uuid)
            },
            'tasks': []
        }

    def _new_task(self, task):
        return {
            'task': {
                'name': task.get_name(),
            },
            'hosts': {}
        }

    def v2_playbook_on_no_hosts_matched(self):
        self.output = "skipping: No match hosts."

    def v2_playbook_on_no_hosts_remaining(self):
        pass

    def v2_playbook_on_task_start(self, task, is_conditional):
        self.results[-1]['tasks'].append(self._new_task(task))

    def v2_playbook_on_play_start(self, play):
        self.results.append(self._new_play(play))

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        summary = {}
        for h in hosts:
            s = stats.summarize(h)
            summary[h] = s

        if self.output:
            pass
        else:
            self.output = {
                'plays': self.results,
                'stats': summary
            }

    def gather_result(self, res):
        if res._task.loop and "results" in res._result and res._host.name in self.item_results:
            res._result.update({"results": self.item_results[res._host.name]})
            del self.item_results[res._host.name]

        self.results[-1]['tasks'][-1]['hosts'][res._host.name] = res._result

    def v2_runner_on_ok(self, res, **kwargs):
        if "ansible_facts" in res._result:
            del res._result["ansible_facts"]

        self.gather_result(res)

    def v2_runner_on_failed(self, res, **kwargs):
        self.gather_result(res)

    def v2_runner_on_unreachable(self, res, **kwargs):
        self.gather_result(res)

    def v2_runner_on_skipped(self, res, **kwargs):
        self.gather_result(res)

    def gather_item_result(self, res):
        self.item_results.setdefault(res._host.name, []).append(res._result)

    def v2_runner_item_on_ok(self, res):
        self.gather_item_result(res)

    def v2_runner_item_on_failed(self, res):
        self.gather_item_result(res)

    def v2_runner_item_on_skipped(self, res):
        self.gather_item_result(res)



