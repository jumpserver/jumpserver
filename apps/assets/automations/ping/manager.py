from assets.const import AutomationTypes, Connectivity
from accounts.const import SecretType
from common.utils import get_logger
from ..base.manager import BasePlaybookManager

logger = get_logger(__name__)


class PingManager(BasePlaybookManager):
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
        platform = kwargs['platform']
        if automation.ping_method.endswith('custom') \
                and account.secret_type == SecretType.SSH_KEY:
            print(f'{platform} {asset} does not support ssh key ping.')
            return []
        self.host_asset_and_account_mapper[host['name']] = (asset, account)
        return host

    def on_host_success(self, host, result):
        asset, account = self.host_asset_and_account_mapper.get(host)
        asset.set_connectivity(Connectivity.OK)
        if not account:
            return
        account.set_connectivity(Connectivity.OK)

    def on_host_error(self, host, error, result):
        asset, account = self.host_asset_and_account_mapper.get(host)
        asset.set_connectivity(Connectivity.ERR)
        if not account:
            return
        account.set_connectivity(Connectivity.ERR)
