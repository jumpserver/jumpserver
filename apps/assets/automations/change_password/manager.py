import os
import shutil
from copy import deepcopy
from collections import defaultdict

import yaml
from django.utils.translation import gettext as _

from ops.ansible import PlaybookRunner, JMSInventory
from ..base.manager import BasePlaybookManager
from assets.automations.methods import platform_automation_methods


class ChangePasswordManager(BasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id_method_mapper = {
            method['id']: method
            for method in platform_automation_methods
        }
        self.method_hosts_mapper = defaultdict(list)

    def host_duplicator(self, host, asset=None, account=None, platform=None, **kwargs):
        accounts = asset.accounts.all()
        if account:
            accounts = accounts.exclude(id=account.id)
        if '*' not in self.automation.accounts:
            accounts = accounts.filter(username__in=self.automation.accounts)

        automation = platform.automation
        change_password_enabled = automation and \
            automation.change_password_enabled and \
            automation.change_password_method and \
            automation.change_password_method in self.id_method_mapper

        if not change_password_enabled:
            host.exclude = _('Change password disabled')
            return [host]

        hosts = []
        for account in accounts:
            h = deepcopy(host)
            h['name'] += '_' + account.username
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'secret_type': account.secret_type,
                'secret': account.secret,
            }
            hosts.append(h)
            self.method_hosts_mapper[automation.change_password_method].append(h['name'])
        return hosts

    def inventory_kwargs(self):
        return {
            'host_duplicator': self.host_duplicator
        }

    def generate_playbook(self):
        playbook = []
        for method_id, host_names in self.method_hosts_mapper.items():
            method = self.id_method_mapper[method_id]
            playbook_dir_path = method['dir']
            playbook_dir_name = os.path.dirname(playbook_dir_path)
            shutil.copytree(playbook_dir_path, self.playbook_dir_path)
            sub_playbook_path = os.path.join(self.playbook_dir_path, playbook_dir_name, 'main.yml')

            with open(sub_playbook_path, 'r') as f:
                host_playbook_play = yaml.safe_load(f)

            plays = []
            for name in host_names:
                play = deepcopy(host_playbook_play)
                play['hosts'] = name
                plays.append(play)

            with open(sub_playbook_path, 'w') as f:
                yaml.safe_dump(plays, f, default_flow_style=False)

            playbook.append({
                'name': method['name'],
                'import_playbook': playbook_dir_name + '/' + 'main.yml'
            })

        with open(self.playbook_path, 'w') as f:
            yaml.safe_dump(playbook, f, default_flow_style=False)

        print("Generate playbook done: " + self.playbook_path)



