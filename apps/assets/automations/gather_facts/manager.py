from common.utils import get_logger
from ..base.manager import BasePlaybookManager

logger = get_logger(__name__)


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
        return host

    def on_host_success(self, host, result):
        info = result.get('Get info', {}).get('res', {}).get('ansible_facts', {}).get('info', {})
        asset = self.host_asset_mapper.get(host)
        if asset and info:
            asset.info = info
            asset.save()
        else:
            logger.error("Not found info, task name must be 'Get info': {}".format(host))




