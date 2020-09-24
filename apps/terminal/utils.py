# -*- coding: utf-8 -*-
#
import os

from django.conf import settings
from django.core.files.storage import default_storage
import jms_storage

from common.utils import get_logger

from .backends import server_replay_storage
from .models import ReplayStorage

logger = get_logger(__name__)


def find_session_replay_local(session):
    # 新版本和老版本的文件后缀不同
    session_path = session.get_rel_replay_path()  # 存在外部存储上的路径
    local_path = session.get_local_path()
    local_path_v1 = session.get_local_path(version=1)

    # 去default storage中查找
    for _local_path in (local_path, local_path_v1, session_path):
        if default_storage.exists(_local_path):
            url = default_storage.url(_local_path)
            return _local_path, url
    return None, None


def download_session_replay(session):
    session_path = session.get_rel_replay_path()  # 存在外部存储上的路径
    local_path = session.get_local_path()
    replay_storages = ReplayStorage.objects.all()
    configs = {
        storage.name: storage.config
        for storage in replay_storages
        if not storage.in_defaults()
    }
    if settings.SERVER_REPLAY_STORAGE:
        configs['SERVER_REPLAY_STORAGE'] = settings.SERVER_REPLAY_STORAGE
    if not configs:
        msg = "Not found replay file, and not remote storage set"
        return None, msg

    # 保存到storage的路径
    target_path = os.path.join(default_storage.base_location, local_path)
    target_dir = os.path.dirname(target_path)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    storage = jms_storage.get_multi_object_storage(configs)
    ok, err = storage.download(session_path, target_path)
    if not ok:
        msg = "Failed download replay file: {}".format(err)
        logger.error(msg)
        return None, msg
    url = default_storage.url(local_path)
    return local_path, url


def get_session_replay_url(session):
    local_path, url = find_session_replay_local(session)
    if local_path is None:
        local_path, url = download_session_replay(session)
    return local_path, url
