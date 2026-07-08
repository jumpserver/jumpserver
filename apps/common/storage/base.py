import os

from django.conf import settings
from django.core.files.storage import default_storage

from common.storage import jms_storage
from common.utils import get_logger, make_dirs
from terminal.models import ReplayStorage

logger = get_logger(__name__)


def get_multi_object_storage(name=None):
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
    # 指定存储名时仅构造该存储, 用于直连文件所在的存储, 避免遍历探测
    if name is not None:
        configs = {name: configs[name]} if name in configs else {}
    if not configs:
        return None
    storage = jms_storage.get_multi_object_storage(configs)
    return storage


class BaseStorageHandler(object):
    NAME = ''

    def __init__(self, obj):
        self.obj = obj

    def get_file_path(self, **kwargs):
        # return remote_path, local_path
        raise NotImplementedError

    def find_local(self):
        raise NotImplementedError

    def get_recorded_storage_name(self):
        # 文件所在存储的名称, 返回 None 表示未记录
        return None

    def download(self):
        # 优先直连已记录的所属存储, 未记录或未命中时回退遍历所有存储 (兼容存量数据)
        recorded_name = self.get_recorded_storage_name()
        storage_names = [recorded_name, None] if recorded_name else [None]

        msg = f"Not found {self.NAME} file, and not remote storage set"
        for name in storage_names:
            storage = get_multi_object_storage(name)
            if not storage:
                continue

            remote_path, local_path = self.get_file_path(storage=storage)
            if not remote_path:
                msg = f'Not found {self.NAME} file'
                continue

            # 保存到storage的路径
            target_path = os.path.join(default_storage.base_location, local_path)
            target_dir = os.path.dirname(target_path)
            if not os.path.isdir(target_dir):
                make_dirs(target_dir, exist_ok=True)

            ok, err = storage.download(remote_path, target_path)
            if ok:
                url = default_storage.url(local_path)
                return local_path, url
            msg = f'Failed download {self.NAME} file: {err}'
        logger.error(msg)
        return None, msg

    def get_file_path_url(self):
        local_path, url = self.find_local()
        if local_path is None:
            local_path, url = self.download()
        return local_path, url
