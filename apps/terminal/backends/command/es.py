# -*- coding: utf-8 -*-
#

from datetime import datetime
from jms_storage.es import ESStorage
from .base import CommandBase
from .models import AbstractSessionCommand


class CommandStore(ESStorage, CommandBase):
    def __init__(self, params):
        super().__init__(params)

    def filter(self, date_from=None, date_to=None,
               user=None, asset=None, system_user=None,
               input=None, session=None):

        if date_from is not None:
            if isinstance(date_from, float):
                date_from = datetime.fromtimestamp(date_from)
        if date_to is not None:
            if isinstance(date_to, float):
                date_to = datetime.fromtimestamp(date_to)

        data = super().filter(date_from=date_from, date_to=date_to,
                              user=user, asset=asset, system_user=system_user,
                              input=input, session=session)
        return AbstractSessionCommand.from_multi_dict(
            [item["_source"] for item in data["hits"] if item]
        )
