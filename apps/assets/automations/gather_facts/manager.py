import os
import shutil
from copy import deepcopy
from collections import defaultdict

import yaml
from django.utils.translation import gettext as _

from ops.ansible import PlaybookRunner
from ..base.manager import BasePlaybookManager
from assets.automations.methods import platform_automation_methods


class GatherFactsManager(BasePlaybookManager):
    method_name = 'gather_facts'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id_method_mapper = {
            method['id']: method
            for method in platform_automation_methods
            if method['method'] == self.method_name
        }
        self.method_hosts_mapper = defaultdict(list)
        self.playbooks = []

    def inventory_kwargs(self):
        return {
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
            self.runtime_dir
        )


