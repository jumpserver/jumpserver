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
        mapping = self.host_asset_and_account_mapper.get(host)
        if not mapping:
            return super().on_host_error(
                host, 'Asset/account mapping not found', result
            )
        asset, account = mapping
        try:
            asset.set_connectivity(Connectivity.OK)
            if account:
                account.set_connectivity(Connectivity.OK)
        except Exception as e:
            super().on_host_error(host, str(e), result)
            print(
                f'\033[31m Update account {getattr(account, "name", "-")} or '
                f'update asset {getattr(asset, "name", "-")} '
                f'connectivity failed: {e} \033[0m\n'
            )
            return
        super().on_host_success(host, result)

    def on_host_error(self, host, error, result):
        super().on_host_error(host, error, result)
        mapping = self.host_asset_and_account_mapper.get(host)
        if not mapping:
            return
        asset, account = mapping
        try:
            error_tp = asset.get_err_connectivity(error)
            asset.set_connectivity(error_tp)
            if not account:
                return
            account.set_connectivity(error_tp)
        except Exception as e:
            print(
                f'\033[31m Update account {getattr(account, "name", "-")} or '
                f'update asset {getattr(asset, "name", "-")} '
                f'connectivity failed: {e} \033[0m\n'
            )
