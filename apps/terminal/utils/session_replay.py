# -*- coding: utf-8 -*-
#
import os
from itertools import groupby, chain

from django.conf import settings
from django.core.files.storage import default_storage

import jms_storage

from common.utils import get_logger, make_dirs
from ..models import ReplayStorage


logger = get_logger(__name__)


def find_session_replay_local(session):
    # 存在外部存储上，所有可能的路径名
    session_paths = session.get_all_possible_relative_path()

    # 存在本地存储上，所有可能的路径名
    local_paths = session.get_all_possible_local_path()

    for _local_path in chain(session_paths, local_paths):
        if default_storage.exists(_local_path):
            url = default_storage.url(_local_path)
            return _local_path, url
    return None, None


def download_session_replay(session):
    replay_storages = ReplayStorage.objects.all()
    configs = {
        storage.name: storage.config
        for storage in replay_storages
        if not storage.type_null_or_server
    }
    if settings.SERVER_REPLAY_STORAGE:
        configs['SERVER_REPLAY_STORAGE'] = settings.SERVER_REPLAY_STORAGE
    if not configs:
        msg = "Not found replay file, and not remote storage set"
        return None, msg
    storage = jms_storage.get_multi_object_storage(configs)

    # 获取外部存储路径名
    session_path = session.find_ok_relative_path_in_storage(storage)
    if not session_path:
        msg = "Not found session replay file"
        return None, msg

    # 通过外部存储路径名后缀，构造真实的本地存储路径
    local_path = session.get_local_path_by_relative_path(session_path)

    # 保存到storage的路径
    target_path = os.path.join(default_storage.base_location, local_path)
    target_dir = os.path.dirname(target_path)
    if not os.path.isdir(target_dir):
        make_dirs(target_dir, exist_ok=True)

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

