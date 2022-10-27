from common.utils import get_logger
from assets.const import AutomationTypes
from orgs.utils import tmp_to_org
from .filter import GatherAccountsFilter
from ...models import Account, GatheredUser
from ..base.manager import BasePlaybookManager

logger = get_logger(__name__)


class GatherAccountsManager(BasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_asset_mapper = {}

    @classmethod
    def method_type(cls):
        return AutomationTypes.gather_accounts

    def host_callback(self, host, asset=None, **kwargs):
        super().host_callback(host, asset=asset, **kwargs)
        self.host_asset_mapper[host['name']] = asset
        return host

    def filter_success_result(self, host, result):
        result = GatherAccountsFilter(host).run(self.method_id_meta_mapper, result)
        return result

    def on_host_success(self, host, result):
        info = result.get('debug', {}).get('res', {}).get('info', {})
        asset = self.host_asset_mapper.get(host)
        org_id = asset.org_id
        if asset and info:
            result = self.filter_success_result(host, info)
            with tmp_to_org(org_id):
                GatheredUser.objects.filter(asset=asset, present=True).update(present=False)
                for username, data in result.items():
                    defaults = {'asset': asset, 'present': True, 'username': username}
                    if data.get('date'):
                        defaults['date_last_login'] = data['date']
                    if data.get('address'):
                        defaults['ip_last_login'] = data['address'][:32]
                    GatheredUser.objects.update_or_create(defaults=defaults, asset=asset, username=username)
        else:
            logger.error("Not found info, task name must be 'Get info': {}".format(host))
