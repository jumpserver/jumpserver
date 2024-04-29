from ops.ansible.cleaner import WorkPostRunCleaner, cleanup_post_run


class BaseRunner(WorkPostRunCleaner):

    def __init__(self, **kwargs):
        self.runner_params = kwargs
        self.clean_workspace = kwargs.pop("clean_workspace", True)

    @classmethod
    def kill_precess(cls, pid):
        return NotImplementedError

    @property
    def clean_dir(self):
        if not self.clean_workspace:
            return None
        return self.private_data_dir

    @property
    def private_data_dir(self):
        return self.runner_params.get('private_data_dir', None)

    def get_event_handler(self):
        _event_handler = self.runner_params.pop("event_handler", None)
        return _event_handler

    def get_status_handler(self):
        _status_handler = self.runner_params.pop("status_handler", None)

        if not _status_handler:
            return

        def _handler(data, **kwargs):
            if self.private_data_dir:
                data["private_data_dir"] = self.private_data_dir
            _status_handler(data, **kwargs)

        return _handler

    def run(self):
        raise NotImplementedError()
