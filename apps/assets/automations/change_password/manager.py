import os
import shutil
from copy import deepcopy
from collections import defaultdict

import yaml
from django.utils.translation import gettext as _

from ops.ansible import PlaybookRunner
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
        self.playbooks = []

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
            host['exclude'] = _('Change password disabled')
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
            method_playbook_dir_path = method['dir']
            method_playbook_dir_name = os.path.basename(method_playbook_dir_path)
            sub_playbook_dir = os.path.join(os.path.dirname(self.playbook_path), method_playbook_dir_name)
            shutil.copytree(method_playbook_dir_path, sub_playbook_dir)
            sub_playbook_path = os.path.join(sub_playbook_dir, 'main.yml')

            with open(sub_playbook_path, 'r') as f:
                host_playbook_play = yaml.safe_load(f)

            if isinstance(host_playbook_play, list):
                host_playbook_play = host_playbook_play[0]

            step = 10
            hosts_grouped = [host_names[i:i+step] for i in range(0, len(host_names), step)]
            for i, hosts in enumerate(hosts_grouped):
                plays = []
                play = deepcopy(host_playbook_play)
                play['hosts'] = ':'.join(hosts)
                plays.append(play)

                playbook_path = os.path.join(sub_playbook_dir, 'part_{}.yml'.format(i))
                with open(playbook_path, 'w') as f:
                    yaml.safe_dump(plays, f)
                self.playbooks.append(playbook_path)

                playbook.append({
                    'name': method['name'] + ' for part {}'.format(i),
                    'import_playbook': os.path.join(method_playbook_dir_name, 'part_{}.yml'.format(i))
                })

        with open(self.playbook_path, 'w') as f:
            yaml.safe_dump(playbook, f)

        print("Generate playbook done: " + self.playbook_path)

    def get_runner(self):
        return PlaybookRunner(
            self.inventory_path,
            self.playbook_path,
            self.playbook_dir_path
        )


