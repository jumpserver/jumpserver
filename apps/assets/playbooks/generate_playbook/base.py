import os
import time
import shutil
from typing import List

from django.conf import settings
from assets.models import Asset


class BaseGeneratePlaybook:
    src_filepath: str

    def __init__(self, assets: List[Asset], strategy):
        self.assets = assets
        self.strategy = strategy
        self.temp_folder = self.temp_folder_path()

    @staticmethod
    def temp_folder_path():
        project_dir = settings.PROJECT_DIR
        tmp_dir = os.path.join(project_dir, 'tmp')
        filepath = os.path.join(tmp_dir, str(time.time()))
        return filepath

    def del_temp_folder(self):
        shutil.rmtree(self.temp_folder)

    def generate_temp_playbook(self):
        src = self.src_filepath
        dst = os.path.join(self.temp_folder, self.strategy)
        shutil.copytree(src, dst)
        return dst
