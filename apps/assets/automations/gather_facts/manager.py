from common.utils import get_logger
from assets.const import AutomationTypes
from ..base.manager import BasePlaybookManager

logger = get_logger(__name__)


class GatherFactsManager(BasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_asset_mapper = {}

    @classmethod
    def method_type(cls):
        return AutomationTypes.gather_facts

    def host_callback(self, host, asset=None, **kwargs):
        super().host_callback(host, asset=asset, **kwargs)
        self.host_asset_mapper[host['name']] = asset
        return host

    def on_host_success(self, host, result):
        info = result.get('debug', {}).get('res', {}).get('info', {})
        asset = self.host_asset_mapper.get(host)
        if asset and info:
            asset.info = info
            asset.save()
        else:
            logger.error("Not found info: {}".format(host))
