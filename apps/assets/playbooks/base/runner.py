import os
import tempfile
import shutil
from typing import List

from django.conf import settings

from assets.models import Asset


class BasePlaybookGenerator:
    def __init__(self, assets: list[Asset], strategy, ansible_connection='ssh'):
        self.assets = assets
        self.strategy = strategy
        self.playbook_dir = self.temp_folder_path()

    def generate(self):
        self.prepare_playbook_dir()
        self.generate_inventory()
        self.generate_playbook()

    def prepare_playbook_dir(self):
        pass

    def generate_inventory(self):
        pass

    def generate_playbook(self):
        pass

    @property
    def base_dir(self):
        tmp_dir = os.path.join(settings.PROJECT_DIR, 'tmp')
        path = os.path.join(tmp_dir, self.strategy)
        return path

    def temp_folder_path(self):
        return tempfile.mkdtemp(dir=self.base_dir)

    def del_temp_folder(self):
        shutil.rmtree(self.playbook_dir)

    def generate_temp_playbook(self):
        src = self.src_filepath
        dst = os.path.join(self.temp_folder, self.strategy)
        shutil.copytree(src, dst)
        return dst
