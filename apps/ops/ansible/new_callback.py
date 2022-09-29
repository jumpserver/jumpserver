
class JMSCallback:
    def event_handler(self, data, runner_config):
        event = data.get('event', None)
        if not event:
            return
        event_data = data.get('event_data', {})
        pass

    def runner_on_ok(self, event_data):
        pass

    def runer_on_failed(self, event_data):
        pass

    def runner_on_skipped(self, event_data):
        pass

    def runner_on_unreachable(self, event_data):
        pass

    def runner_on_start(self, event_data):
        pass

    def runer_retry(self, event_data):
        pass

    def runner_on_file_diff(self, event_data):
        pass

    def runner_item_on_failed(self, event_data):
        pass

    def runner_item_on_skipped(self, event_data):
        pass

    def playbook_on_play_start(self, event_data):
        pass

    def playbook_on_stats(self, event_data):
        pass

    def playbook_on_include(self, event_data):
        pass

    def playbook_on_notify(self, event_data):
        pass

    def playbook_on_vars_prompt(self, event_data):
        pass

    def playbook_on_handler_task_start(self, event_data):
        pass

    def playbook_on_no_hosts_matched(self, event_data):
        pass

    def playbook_on_no_hosts_remaining(self, event_data):
        pass

    def warning(self):
        pass

    def status_handler(self):
        pass
