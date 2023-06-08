from itertools import chain

from terminal.models import default_storage
from .base import BaseStorageHandler


class ReplayStorageHandler(BaseStorageHandler):
    NAME = 'REPLAY'

    def get_file_path(self, **kwargs):
        storage = kwargs['storage']
        # 获取外部存储路径名
        session_path = self.obj.find_ok_relative_path_in_storage(storage)
        if not session_path:
            return None

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
