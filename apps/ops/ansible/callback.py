from collections import defaultdict


class DefaultCallback:
    def __init__(self):
        self.result = dict(
            ok=defaultdict(dict),
            failures=defaultdict(dict),
            dark=defaultdict(dict),
            skipped=defaultdict(dict),
        )
        self.summary = dict(
            ok=[],
            failures={},
            dark={},
            skipped=[],
        )
        self.status = 'running'
        self.finished = False

    def is_success(self):
        return self.status != 'successful'

    def event_handler(self, data, **kwargs):
        event = data.get('event', None)
        if not event:
            return
        event_data = data.get('event_data', {})
        host = event_data.get('remote_addr', '')
        task = event_data.get('task', '')
        res = event_data.get('res', {})
        handler = getattr(self, event, self.on_any)
        handler(event_data, host=host, task=task, res=res)

    def runner_on_ok(self, event_data, host=None, task=None, res=None):
        detail = {
            'action': event_data.get('task_action', ''),
            'res': res,
            'rc': res.get('rc', 0),
            'stdout': res.get('stdout', ''),
        }
        self.result['ok'][host][task] = detail

    def runer_on_failed(self, event_data, host=None, task=None, res=None, **kwargs):
        detail = {
            'action': event_data.get('task_action', ''),
            'res': res,
            'rc': res.get('rc', 0),
            'stdout': res.get('stdout', ''),
            'stderr': ';'.join([res.get('stderr', ''), res.get('msg', '')]).strip(';')
        }
        self.result['failures'][host][task] = detail

    def runner_on_skipped(self, event_data, host=None, task=None, **kwargs):
        detail = {
            'action': event_data.get('task_action', ''),
            'res': {},
            'rc': 0,
        }
        self.result['skipped'][host][task] = detail

    def runner_on_unreachable(self, event_data, host=None, task=None, res=None, **kwargs):
        detail = {
            'action': event_data.get('task_action', ''),
            'res': res,
            'rc': 255,
            'stderr': ';'.join([res.get('stderr', ''), res.get('msg', '')]).strip(';')
        }
        self.result['dark'][host][task] = detail

    def runner_on_start(self, event_data, **kwargs):
        pass

    def runer_retry(self, event_data, **kwargs):
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
        failed = []
        for i in ['dark', 'failures']:
            for host, tasks in self.result[i].items():
                failed.append(host)
                error = ''
                for task, detail in tasks.items():
                    error += f'{task}: {detail["stderr"]};'
                self.summary[i][host] = error.strip(';')
        self.summary['ok'] = list(set(self.result['ok'].keys()) - set(failed))
        self.summary['skipped'] = list(set(self.result['skipped'].keys()) - set(failed))

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

    def warning(self, event_data, **kwargs):
        pass

    def on_any(self, event_data, **kwargs):
        pass

    def status_handler(self, data, **kwargs):
        self.status = data.get('status', 'unknown')
