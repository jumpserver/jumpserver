# coding: utf-8
import abc


class CommandBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def save(self, command):
        pass

    @abc.abstractmethod
    def bulk_save(self, commands):
        pass

    @abc.abstractmethod
    def filter(self, date_from=None, date_to=None,
               user=None, asset=None, system_user=None,
               input=None, session=None):
        pass

    @abc.abstractmethod
    def count(self, date_from=None, date_to=None,
              user=None, asset=None, system_user=None,
              input=None, session=None):
        pass

