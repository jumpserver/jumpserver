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
        self.is_sync_account = self.execution.snapshot.get('is_sync_account')

    @classmethod
    def method_type(cls):
        return AutomationTypes.gather_accounts

    def host_callback(self, host, asset=None, **kwargs):
        super().host_callback(host, asset=asset, **kwargs)
        self.host_asset_mapper[host['name']] = asset
        return host

    def filter_success_result(self, tp, result):
        result = GatherAccountsFilter(tp).run(self.method_id_meta_mapper, result)
        return result
    @staticmethod
    def generate_data(asset, result):
        data = []
        for username, info in result.items():
            d = {'asset': asset, 'username': username, 'present': True}
            if info.get('date'):
                d['date_last_login'] = info['date']
            if info.get('address'):
                d['address_last_login'] = info['address'][:32]
            data.append(d)
        return data

    def update_or_create_accounts(self, asset, result):
        data = self.generate_data(asset, result)
        with tmp_to_org(asset.org_id):
            gathered_accounts = []
            GatheredAccount.objects.filter(asset=asset, present=True).update(present=False)
            for d in data:
                username = d['username']
                gathered_account, __ = GatheredAccount.objects.update_or_create(
                    defaults=d, asset=asset, username=username,
                )
                gathered_accounts.append(gathered_account)
            if not self.is_sync_account:
                return
            GatheredAccount.sync_accounts(gathered_accounts)

    def on_host_success(self, host, result):
        info = result.get('debug', {}).get('res', {}).get('info', {})
        asset = self.host_asset_mapper.get(host)
        if asset and info:
            result = self.filter_success_result(asset.type, info)
            self.update_or_create_accounts(asset, result)
        else:
            logger.error("Not found info".format(host))
