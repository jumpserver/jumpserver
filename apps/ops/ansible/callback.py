# ~*~ coding: utf-8 ~*~

from ansible.plugins.callback import CallbackBase


class AdHocResultCallback(CallbackBase):
    """
    AdHoc result Callback
    """
    def __init__(self, display=None):
        # result_raw example: {
        #   "ok": {"hostname": []},
        #   "failed": {"hostname": []},
        #   "unreachable: {"hostname": []},
        #   "skipped": {"hostname": []},
        # }
        # results_summary example: {
        #   "contacted": {"hostname",...},
        #   "dark": {"hostname": ["error",...],},
        # }
        self.results_raw = dict(ok={}, failed={}, unreachable={}, skipped={})
        self.results_summary = dict(contacted=set(), dark={})
        super().__init__(display)

    def gather_result(self, t, host, res):
        if self.results_raw[t].get(host):
            self.results_raw[t][host].append(res)
        else:
            self.results_raw[t][host] = [res]
        self.clean_result(t, host, res)

    def clean_result(self, t, host, res):
        contacted = self.results_summary["contacted"]
        dark = self.results_summary["dark"]
        if t in ("ok", "skipped") and host not in dark:
            contacted.add(host)
        else:
            dark[host].append(res)
            if host in contacted:
                contacted.remove(dark)

    def runner_on_ok(self, host, res):
        self.gather_result("ok", host, res)

    def runner_on_failed(self, host, res, ignore_errors=False):
        self.gather_result("failed", host, res)

    def runner_on_unreachable(self, host, res):
        self.gather_result("unreachable", host, res)

    def runner_on_skipped(self, host, item=None):
        self.gather_result("skipped", host, item)


class CommandResultCallback(AdHocResultCallback):
    def __init__(self, display=None):
        self.results_command = dict()
        super().__init__(display)

    def gather_result(self, t, host, res):
        super().gather_result(t, host, res)
        self.gather_cmd(t, host, res)

    def gather_cmd(self, t, host, res):
        cmd = {}
        if t == "ok":
            cmd['cmd'] = res.get('cmd')
            cmd['stderr'] = res.get('stderr')
            cmd['stdout'] = res.get('stdout')
            cmd['rc'] = res.get('rc')
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



