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

    @staticmethod
    def get_gathered_info(result):
        result = result or {}
        if not isinstance(result, dict):
            return {}
        for task_result in reversed(list(result.values())):
            if not isinstance(task_result, dict):
                continue
            response = task_result.get('res', {})
            facts = response.get('ansible_facts', {})
            if 'info' in facts:
                return facts['info']
        return result.get('debug', {}).get('res', {}).get('info', {})

    def on_host_success(self, host, result):
        info = self.get_gathered_info(result)
        asset = self.host_asset_mapper.get(host)
        if asset and info:
            try:
                info = self.format_asset_info(asset.type, info)
                asset.gathered_info = info
                asset.save(update_fields=['gathered_info'])
            except Exception as error:
                logger.exception(
                    'Save gathered facts failed: host=%s', host
                )
                return super().on_host_error(
                    host, str(error), result
                )
            super().on_host_success(host, result)
        else:
            logger.error("Not found info: {}".format(host))
            super().on_host_error(
                host, 'Gathered facts result is empty', result
            )
