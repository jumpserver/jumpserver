# -*- coding: utf-8 -*-
#

from .base import ObjectStorage, LogStorage


class MultiObjectStorage(ObjectStorage):

    def __init__(self, configs):
        self.configs = configs
        self.storage_list = []
        self.init_storage_list()

    def init_storage_list(self):
        from . import get_object_storage
        if isinstance(self.configs, dict):
            configs = self.configs.values()
        else:
            configs = self.configs

        for config in configs:
            try:
                storage = get_object_storage(config)
                self.storage_list.append(storage)
            except Exception:
                pass

    def upload(self, src, target):
        success = []
        msg = []

        for storage in self.storage_list:
            ok, err = storage.upload(src, target)
            success.append(ok)
            msg.append(err)

        return success, msg

    def download(self, src, target):
        success = False
        msg = None

        for storage in self.storage_list:
            try:
                if not storage.exists(src):
                    continue
                ok, msg = storage.download(src, target)
                if ok:
                    success = True
                    msg = ''
                    break
            except:
                pass
        return success, msg

    def delete(self, path):
        success = True
        msg = None

        for storage in self.storage_list:
            try:
                if storage.exists(path):
                    ok, msg = storage.delete(path)
                    if not ok:
                        success = False
            except:
                pass
        return success, msg

    def exists(self, path):
        for storage in self.storage_list:
            try:
                if storage.exists(path):
                    return True
            except:
                pass
        return False
