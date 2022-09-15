import os
import yaml
from typing import List

from django.conf import settings
from assets.models import Asset
from .base import BaseGeneratePlaybook


class GenerateVerifyPlaybook(BaseGeneratePlaybook):

    def __init__(
            self, assets: List[Asset], strategy, usernames
    ):
        super().__init__(assets, strategy)
        self.relation_asset_map = self.get_account_relation_asset_map(usernames)

    def get_account_relation_asset_map(self, usernames):
        # TODO 没特权用户的资产 要考虑网关
        complete_map = {
            asset: list(asset.accounts.all())
            for asset in self.assets
        }

        if '*' in usernames:
            return complete_map

        relation_map = {}
        for asset, accounts in complete_map.items():
            account_map = {account.username: account for account in accounts}
            accounts = [account_map[i] for i in (set(usernames) & set(account_map))]
            if not accounts:
                continue
            relation_map[asset] = accounts
        return relation_map

    @property
    def src_filepath(self):
        return os.path.join(
            settings.BASE_DIR, 'assets', 'playbooks', 'strategy',
            'verify', 'roles', self.strategy
        )

    def generate_hosts(self):
        host_pathname = os.path.join(self.temp_folder, 'hosts')
        with open(host_pathname, 'w', encoding='utf8') as f:
            for asset in self.relation_asset_map.keys():
                f.write(f'{asset.name}\n')

    def generate_host_vars(self):
        host_vars_pathname = os.path.join(self.temp_folder, 'hosts', 'host_vars')
        os.makedirs(host_vars_pathname, exist_ok=True)
        for asset, accounts in self.relation_asset_map.items():
            account_info = []
            for account in accounts:
                private_key_filename = f'{asset.name}_{account.username}' if account.private_key else ''
                account_info.append({
                    'username': account.username,
                    'password': account.password,
                    'private_key_filename': private_key_filename,
                })
            host_vars = {
                'ansible_host': asset.get_target_ip(),
                'ansible_port': asset.get_target_ssh_port(),  # TODO 需要根绝协议取端口号
                'account_info': account_info,
            }
            pathname = os.path.join(host_vars_pathname, f'{asset.name}.yml')
            with open(pathname, 'w', encoding='utf8') as f:
                f.write(yaml.dump(host_vars, allow_unicode=True))

    def generate_secret_key_files(self):
        file_pathname = os.path.join(self.temp_folder, self.strategy, 'files')
        os.makedirs(file_pathname, exist_ok=True)
        for asset, accounts in self.relation_asset_map.items():
            for account in accounts:
                if account.private_key:
                    path_name = os.path.join(file_pathname, f'{asset.name}_{account.username}')
                    with open(path_name, 'w', encoding='utf8') as f:
                        f.write(account.private_key)

    def execute(self):
        self.generate_temp_playbook()
        self.generate_hosts()
        self.generate_host_vars()
        self.generate_secret_key_files()
        # self.generate_role_main() # TODO Linux 暂时不需要
