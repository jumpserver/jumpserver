from terminal.models import default_storage
from .base import BaseStorageHandler


class FTPFileStorageHandler(BaseStorageHandler):
    NAME = 'FTP'

    def get_file_path(self, **kwargs):
        return self.obj.filepath, self.obj.filepath

    def find_local(self):
        local_path = self.obj.filepath
        # 去default storage中查找
        if default_storage.exists(local_path):
            url = default_storage.url(local_path)
            return local_path, url
        return None, None
