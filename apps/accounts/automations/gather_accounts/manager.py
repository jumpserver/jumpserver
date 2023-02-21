from accounts.const import AutomationTypes
from accounts.models import GatheredAccount
from common.utils import get_logger
from orgs.utils import tmp_to_org
from .filter import GatherAccountsFilter
from ..base.manager import AccountBasePlaybookManager

logger = get_logger(__name__)


class GatherAccountsManager(AccountBasePlaybookManager):
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

    @staticmethod
    def update_or_create_gathered_accounts(asset, result):
        with tmp_to_org(asset.org_id):
            GatheredAccount.objects.filter(asset=asset, present=True).update(present=False)
            for username, data in result.items():
                d = {'asset': asset, 'username': username, 'present': True}
                if data.get('date'):
                    d['date_last_login'] = data['date']
                if data.get('address'):
                    d['address_last_login'] = data['address'][:32]
                GatheredAccount.objects.update_or_create(
                    defaults=d, asset=asset, username=username,
                )

    def on_host_success(self, host, result):
        info = result.get('debug', {}).get('res', {}).get('info', {})
        asset = self.host_asset_mapper.get(host)
        if asset and info:
            result = self.filter_success_result(asset.type, info)
            self.update_or_create_gathered_accounts(asset, result)
        else:
            logger.error("Not found info".format(host))
