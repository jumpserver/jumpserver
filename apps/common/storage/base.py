import os

import jms_storage

from django.conf import settings

from terminal.models import default_storage, ReplayStorage
from common.utils import get_logger, make_dirs

logger = get_logger(__name__)


class BaseStorageHandler(object):
    NAME = ''

    def __init__(self, obj):
        self.obj = obj

    def get_file_path(self, **kwargs):
        # return remote_path, local_path
        raise NotImplementedError

    def find_local(self):
        raise NotImplementedError

    def download(self):
        replay_storages = ReplayStorage.objects.all()
        configs = {}
        for storage in replay_storages:
            if storage.type_sftp:
                continue
            if storage.type_null_or_server:
                continue
            configs[storage.name] = storage.config
        if settings.SERVER_REPLAY_STORAGE:
            configs['SERVER_REPLAY_STORAGE'] = settings.SERVER_REPLAY_STORAGE
        if not configs:
            msg = f"Not found {self.NAME} file, and not remote storage set"
            return None, msg
        storage = jms_storage.get_multi_object_storage(configs)

        remote_path, local_path = self.get_file_path(storage=storage)
        if not remote_path:
            msg = f'Not found {self.NAME} file'
            logger.error(msg)
            return None, msg

        # 保存到storage的路径
        target_path = os.path.join(default_storage.base_location, local_path)
        target_dir = os.path.dirname(target_path)
        if not os.path.isdir(target_dir):
            make_dirs(target_dir, exist_ok=True)

        ok, err = storage.download(remote_path, target_path)
        if not ok:
            msg = f'Failed download {self.NAME} file: {err}'
            logger.error(msg)
            return None, msg
        url = default_storage.url(local_path)
        return local_path, url

    def get_file_path_url(self):
        local_path, url = self.find_local()
        if local_path is None:
            local_path, url = self.download()
        return local_path, url
