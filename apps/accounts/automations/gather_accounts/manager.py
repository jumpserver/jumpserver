from collections import defaultdict

from accounts.const import AutomationTypes
from accounts.models import GatheredAccount
from assets.models import Asset
from common.utils import get_logger
from orgs.utils import tmp_to_org
from users.models import User
from .filter import GatherAccountsFilter
from ..base.manager import AccountBasePlaybookManager
from ...notifications import GatherAccountChangeMsg

logger = get_logger(__name__)


class GatherAccountsManager(AccountBasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_asset_mapper = {}
        self.asset_account_info = {}

        self.asset_username_mapper = defaultdict(set)
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

    def generate_data(self, asset, result):
        data = []
        for username, info in result.items():
            self.asset_username_mapper[str(asset.id)].add(username)
            d = {'asset': asset, 'username': username, 'present': True}
            if info.get('date'):
                d['date_last_login'] = info['date']
            if info.get('address'):
                d['address_last_login'] = info['address'][:32]
            data.append(d)
        return data

    def collect_asset_account_info(self, asset, result):
        data = self.generate_data(asset, result)
        self.asset_account_info[asset] = data

    def on_host_success(self, host, result):
        info = result.get('debug', {}).get('res', {}).get('info', {})
        asset = self.host_asset_mapper.get(host)
        if asset and info:
            result = self.filter_success_result(asset.type, info)
            self.collect_asset_account_info(asset, result)
        else:
            logger.error(f'Not found {host} info')

    def update_or_create_accounts(self):
        for asset, data in self.asset_account_info.items():
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
                    continue
                GatheredAccount.sync_accounts(gathered_accounts)

    def run(self, *args, **kwargs):
        super().run(*args, **kwargs)
        users, change_info = self.generate_send_users_and_change_info()
        self.update_or_create_accounts()
        self.send_email_if_need(users, change_info)

    def generate_send_users_and_change_info(self):
        recipients = self.execution.recipients
        if not self.asset_username_mapper or not recipients:
            return None, None

        users = User.objects.filter(id__in=recipients)
        if not users:
            return users, None

        asset_ids = self.asset_username_mapper.keys()
        assets = Asset.objects.filter(id__in=asset_ids)
        gather_accounts = GatheredAccount.objects.filter(asset_id__in=asset_ids, present=True)
        asset_id_map = {str(asset.id): asset for asset in assets}
        asset_id_username = list(assets.values_list('id', 'accounts__username'))
        asset_id_username.extend(list(gather_accounts.values_list('asset_id', 'username')))

        system_asset_username_mapper = defaultdict(set)
        for asset_id, username in asset_id_username:
            system_asset_username_mapper[str(asset_id)].add(username)

        change_info = {}
        for asset_id, usernames in self.asset_username_mapper.items():
            system_usernames = system_asset_username_mapper.get(asset_id)

            if not system_usernames:
                continue

            add_usernames = usernames - system_usernames
            remove_usernames = system_usernames - usernames
            k = f'{asset_id_map[asset_id]}[{asset_id}]'

            if not add_usernames and not remove_usernames:
                continue

            change_info[k] = {
                'add_usernames': ', '.join(add_usernames),
                'remove_usernames': ', '.join(remove_usernames),
            }

        return users, change_info

    @staticmethod
    def send_email_if_need(users, change_info):
        if not users or not change_info:
            return

        for user in users:
            GatherAccountChangeMsg(user, change_info).publish_async()
