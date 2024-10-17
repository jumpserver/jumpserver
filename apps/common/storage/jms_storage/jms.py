# -*- coding: utf-8 -*-
#
import os
from .base import ObjectStorage, LogStorage


class JMSReplayStorage(ObjectStorage):
    def __init__(self, config):
        self.client = config.get("SERVICE")

    def upload(self, src, target):
        session_id = os.path.basename(target).split('.')[0]
        ok = self.client.push_session_replay(src, session_id)
        return ok, None

    def delete(self, path):
        return False, Exception("Not support not")

    def exists(self, path):
        return False

    def download(self, src, target):
        return False, Exception("Not support not")

    @property
    def type(self):
        return 'jms'


class JMSCommandStorage(LogStorage):
    def __init__(self, config):
        self.client = config.get("SERVICE")
        if not self.client:
            raise Exception("Not found app service")

    def save(self, command):
        return self.client.push_session_command([command])

    def bulk_save(self, command_set, raise_on_error=True):
        return self.client.push_session_command(command_set)

    def filter(self, date_from=None, date_to=None,
               user=None, asset=None, account=None,
               input=None, session=None):
        pass

    def count(self, date_from=None, date_to=None,
              user=None, asset=None, account=None,
              input=None, session=None):
        pass
