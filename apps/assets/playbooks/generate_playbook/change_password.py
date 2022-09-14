import os
import yaml
import jinja2
from typing import List

from django.conf import settings
from assets.models import Asset
from .base import BaseGeneratePlaybook


class GenerateChangePasswordPlaybook(BaseGeneratePlaybook):

    def __init__(
            self, assets: List[Asset], strategy, usernames, password='',
            private_key='', public_key='', key_strategy=''
    ):
        super().__init__(assets, strategy)
        self.password = password
        self.public_key = public_key
        self.private_key = private_key
        self.key_strategy = key_strategy
        self.relation_asset_map = self.get_username_relation_asset_map(usernames)

    def get_username_relation_asset_map(self, usernames):
        # TODO 没牛逼用户的资产 网关

        complete_map = {
            asset: list(asset.accounts.value_list('username', flat=True))
            for asset in self.assets
        }

        if '*' in usernames:
            return complete_map

        relation_map = {}
        for asset, usernames in complete_map.items():
            relation_map[asset] = list(set(usernames) & set(usernames))
        return relation_map

    @property
    def src_filepath(self):
        return os.path.join(
            settings.BASE_DIR, 'assets', 'playbooks', 'strategy',
            'change_password', 'roles', self.strategy
        )

    def generate_hosts(self):
        host_pathname = os.path.join(self.temp_folder, 'hosts')
        with open(host_pathname, 'w', encoding='utf8') as f:
            for asset in self.relation_asset_map.keys():
                f.write(f'{asset.name}\n')

    def generate_host_vars(self):
        host_vars_pathname = os.path.join(self.temp_folder, 'hosts', 'host_vars')
        os.makedirs(host_vars_pathname, exist_ok=True)
        for asset, usernames in self.relation_asset_map.items():
            host_vars = {
                'ansible_host': asset.get_target_ip(),
                'ansible_port': asset.get_target_ssh_port(),  # TODO 需要根绝协议取端口号
                'ansible_user': asset.admin_user.username,
                'ansible_pass': asset.admin_user.username,
                'ansible_connection': 'ssh',
                'usernames': usernames,
            }
            pathname = os.path.join(host_vars_pathname, f'{asset.name}.yml')
            with open(pathname, 'w', encoding='utf8') as f:
                f.write(yaml.dump(host_vars, allow_unicode=True))

    def generate_secret_key_files(self):
        if not self.private_key and not self.public_key:
            return

        file_pathname = os.path.join(self.temp_folder, self.strategy, 'files')
        public_pathname = os.path.join(file_pathname, 'id_rsa.pub')
        private_pathname = os.path.join(file_pathname, 'id_rsa')

        os.makedirs(file_pathname, exist_ok=True)
        with open(public_pathname, 'w', encoding='utf8') as f:
            f.write(self.public_key)
        with open(private_pathname, 'w', encoding='utf8') as f:
            f.write(self.private_key)

    def generate_role_main(self):
        task_main_pathname = os.path.join(self.temp_folder, 'main.yaml')
        context = {
            'password': self.password,
            'key_strategy': self.key_strategy,
            'private_key_file': 'id_rsa' if self.private_key else '',
            'exclusive': 'no' if self.key_strategy == 'all' else 'yes',
            'jms_key': self.public_key.split()[2].strip() if self.public_key else '',
        }
        with open(task_main_pathname, 'r+', encoding='utf8') as f:
            string_var = f.read()
            f.seek(0, 0)
            response = jinja2.Template(string_var).render(context)
            results = yaml.safe_load(response)
            f.write(yaml.dump(results, allow_unicode=True))

    def execute(self):
        self.generate_temp_playbook()
        self.generate_hosts()
        self.generate_host_vars()
        self.generate_secret_key_files()
        self.generate_role_main()
