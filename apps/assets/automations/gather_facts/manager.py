from assets.const import AutomationTypes
from common.utils import get_logger
from .format_asset_info import FormatAssetInfo
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

    def format_asset_info(self, tp, info):
        info = FormatAssetInfo(tp).run(self.method_id_meta_mapper, info)
        return info

    def on_host_success(self, host, result):
        info = result.get('debug', {}).get('res', {}).get('info', {})
        asset = self.host_asset_mapper.get(host)
        if asset and info:
            info = self.format_asset_info(asset.type, info)
            asset.gathered_info = info
            asset.save(update_fields=['gathered_info'])
        else:
            logger.error("Not found info: {}".format(host))
