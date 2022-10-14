from ..base.manager import BasePlaybookManager


class GatherFactsManager(BasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_asset_mapper = {}

    @classmethod
    def method_type(cls):
        return 'gather_facts'

    def host_callback(self, host, asset=None, **kwargs):
        super().host_callback(host, asset=asset, **kwargs)
        self.host_asset_mapper[host['name']] = asset

    def on_host_success(self, host, result):
        print("Host: {}".format(host))
        print("Result: {}".format(result))




