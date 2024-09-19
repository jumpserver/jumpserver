import json
import os
import tarfile
from itertools import chain

from django.core.files.storage import default_storage

from common.utils import make_dirs, get_logger
from terminal.models import Session
from .base import BaseStorageHandler, get_multi_object_storage

logger = get_logger(__name__)


class ReplayStorageHandler(BaseStorageHandler):
    NAME = 'REPLAY'

    def get_file_path(self, **kwargs):
        storage = kwargs['storage']
        # 获取外部存储路径名
        session_path = self.obj.find_ok_relative_path_in_storage(storage)
        if not session_path:
            return None, None

        # 通过外部存储路径名后缀，构造真实的本地存储路径
        return session_path, self.obj.get_local_path_by_relative_path(session_path)

    def find_local(self):
        # 存在外部存储上，所有可能的路径名
        session_paths = self.obj.get_all_possible_relative_path()

        # 存在本地存储上，所有可能的路径名
        local_paths = self.obj.get_all_possible_local_path()

        for _local_path in chain(session_paths, local_paths):
            if default_storage.exists(_local_path):
                url = default_storage.url(_local_path)
                return _local_path, url
        return None, f'{self.NAME} not found.'


class SessionPartReplayStorageHandler(object):
    Name = 'SessionPartReplayStorageHandler'

    def __init__(self, obj: Session):
        self.obj = obj

    def find_local_part_file_path(self, part_filename):
        local_path = self.obj.get_replay_part_file_local_storage_path(part_filename)
        if default_storage.exists(local_path):
            url = default_storage.url(local_path)
            return local_path, url
        return None, '{} not found.'.format(part_filename)

    def download_part_file(self, part_filename):
        storage = get_multi_object_storage()
        if not storage:
            msg = "Not found {} file, and not remote storage set".format(part_filename)
            return None, msg
        local_path = self.obj.get_replay_part_file_local_storage_path(part_filename)
        remote_path = self.obj.get_replay_part_file_relative_path(part_filename)

        # 保存到storage的路径
        target_path = os.path.join(default_storage.base_location, local_path)

        target_dir = os.path.dirname(target_path)
        if not os.path.isdir(target_dir):
            make_dirs(target_dir, exist_ok=True)

        ok, err = storage.download(remote_path, target_path)
        if not ok:
            msg = 'Failed download {} file: {}'.format(part_filename, err)
            logger.error(msg)
            return None, msg
        url = default_storage.url(local_path)
        return local_path, url

    def get_part_file_path_url(self, part_filename):
        local_path, url = self.find_local_part_file_path(part_filename)
        if local_path is None:
            local_path, url = self.download_part_file(part_filename)
        return local_path, url

    def prepare_offline_tar_file(self):
        replay_meta_filename = '{}.replay.json'.format(self.obj.id)
        meta_local_path, url_or_error = self.get_part_file_path_url(replay_meta_filename)
        if not meta_local_path:
            raise FileNotFoundError(f'{replay_meta_filename} not found: {url_or_error}')
        meta_local_abs_path = os.path.join(default_storage.base_location, meta_local_path)
        with open(meta_local_abs_path, 'r') as f:
            meta_data = json.load(f)
        if not meta_data:
            raise FileNotFoundError(f'{replay_meta_filename} is empty')
        part_filenames = [part_file.get('name') for part_file in meta_data.get('files', [])]
        for part_filename in part_filenames:
            if not part_filename:
                continue
            local_path, url_or_error = self.get_part_file_path_url(part_filename)
            if not local_path:
                raise FileNotFoundError(f'{part_filename} not found: {url_or_error}')
        dir_path = os.path.dirname(meta_local_abs_path)
        offline_filename = '{}.tar'.format(self.obj.id)
        offline_filename_abs_path = os.path.join(dir_path, offline_filename)
        if not os.path.exists(offline_filename_abs_path):
            with tarfile.open(offline_filename_abs_path, 'w') as f:
                f.add(str(meta_local_abs_path), arcname=replay_meta_filename)
                for part_filename in part_filenames:
                    local_abs_path = os.path.join(dir_path, part_filename)
                    f.add(local_abs_path, arcname=part_filename)
        return open(offline_filename_abs_path, 'rb')
