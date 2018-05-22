# -*- coding: utf-8 -*-
#

from jms_storage.es import ESStorage
from .base import CommandBase
from .models import AbstractSessionCommand


class CommandStore(ESStorage, CommandBase):
    def __init__(self, params):
        super().__init__(params)

    def filter(self, date_from=None, date_to=None,
               user=None, asset=None, system_user=None,
               input=None, session=None):

        data = super().filter(date_from=date_from, date_to=date_to,
                              user=user, asset=asset, system_user=system_user,
                              input=input, session=session)
        return AbstractSessionCommand.from_multi_dict(
            [item["_source"] for item in data["hits"] if item]
        )
