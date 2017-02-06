# coding: utf-8
import abc


class CommandBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def save(self, proxy_log_id, user, asset, system_user,
             command_no, command, output, timestamp):
        pass

    @abc.abstractmethod
    def filter(self, date_from=None, date_to=None, user='',
               asset='', system_user='', command=''):
        pass



