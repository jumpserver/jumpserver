# -*- coding: utf-8 -*-
#

from jms_es_storage import ESStore
from .base import CommandBase


class CommandStore(CommandBase, ESStore):
    def __init__(self):
        ESStore.__init__(self, hosts=["http://elastic:changeme@localhost:9200"])

    def save(self, command):
        return ESStore.save(self, command)

    def bulk_save(self, commands):
        return ESStore.bulk_save(self, commands)

    def filter(self, date_from=None, date_to=None,
               user=None, asset=None, system_user=None,
               input=None, session=None):

        data = ESStore.filter(
            self, date_from=date_from, date_to=date_to,
            user=user, asset=asset, system_user=system_user,
            input=input, session=session
        )
        return [item["_source"] for item in data["hits"] if item]
