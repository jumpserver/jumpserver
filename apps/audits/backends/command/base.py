# coding: utf-8
import abc


class CommandBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def save(self, proxy_log_id, user, asset, system_user,
             command_no, command, output, timestamp):
        pass

    @abc.abstractmethod
    def filter(self, date_from_ts=None, date_to_ts=None, user='',
               asset='', system_user='', command='', proxy_log_id=0):
        pass



