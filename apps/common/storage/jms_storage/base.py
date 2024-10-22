# -*- coding: utf-8 -*-
#

import abc


class ObjectStorage(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def upload(self, src, target):
        return None, None

    @abc.abstractmethod
    def download(self, src, target):
        pass

    @abc.abstractmethod
    def delete(self, path):
        pass

    @abc.abstractmethod
    def exists(self, path):
        pass

    def is_valid(self, src, target):
        ok, msg = self.upload(src=src, target=target)
        if not ok:
            return False
        self.delete(path=target)
        return True


class LogStorage(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save(self, command):
        pass

    @abc.abstractmethod
    def bulk_save(self, command_set, raise_on_error=True):
        pass

    @abc.abstractmethod
    def filter(self, date_from=None, date_to=None,
               user=None, asset=None, account=None,
               input=None, session=None):
        pass

    @abc.abstractmethod
    def count(self, date_from=None, date_to=None,
              user=None, asset=None, account=None,
              input=None, session=None):
        pass
