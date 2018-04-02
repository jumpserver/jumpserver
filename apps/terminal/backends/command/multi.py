# -*- coding: utf-8 -*-
#

from .base import CommandBase


class CommandStore(CommandBase):
    def __init__(self, storage_list):
        self.storage_list = storage_list

    def filter(self, **kwargs):
        queryset = []

        for storage in self.storage_list:
            queryset.extend(storage.filter(**kwargs))
        return sorted(queryset, key=lambda command: command.timestamp, reverse=True)

    def count(self, **kwargs):
        amount = 0
        for storage in self.storage_list:
            amount += storage.count(**kwargs)
        return amount

    def save(self, command):
        pass

    def bulk_save(self, commands):
        pass
