# coding: utf-8
import abc


class RecordBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def save(self, proxy_log_id, output, timestamp):
        pass

    @abc.abstractmethod
    def filter(self, date_from_ts=None, proxy_log_id=None):
        pass
