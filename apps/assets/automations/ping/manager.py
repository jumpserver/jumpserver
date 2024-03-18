from assets.const import AutomationTypes, Connectivity
from common.utils import get_logger
from ..base.manager import BasePlaybookManager

logger = get_logger(__name__)


class PingManager(BasePlaybookManager):
    ansible_account_prefer = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_asset_and_account_mapper = {}

    @classmethod
    def method_type(cls):
        return AutomationTypes.ping

    def host_callback(self, host, asset=None, account=None, automation=None, **kwargs):
        super().host_callback(
            host, asset=asset, account=account, automation=automation, **kwargs
        )
        self.host_asset_and_account_mapper[host['name']] = (asset, account)
        return host

    def on_host_success(self, host, result):
        asset, account = self.host_asset_and_account_mapper.get(host)
        try:
            asset.set_connectivity(Connectivity.OK)
            if not account:
                return
            account.set_connectivity(Connectivity.OK)
        except Exception as e:
            print(f'\033[31m Update account {account.name} or '
                  f'update asset {asset.name} connectivity failed: {e} \033[0m\n')

    def on_host_error(self, host, error, result):
        asset, account = self.host_asset_and_account_mapper.get(host)
        try:
            asset.set_connectivity(Connectivity.ERR)
            if not account:
                return
            account.set_connectivity(Connectivity.ERR)
        except Exception as e:
            print(f'\033[31m Update account {account.name} or '
                  f'update asset {asset.name} connectivity failed: {e} \033[0m\n')
