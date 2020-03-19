# -*- coding: utf-8 -*-
#

from datetime import datetime
from jms_storage.es import ESStorage
from common.utils import get_logger
from .base import CommandBase
from .models import AbstractSessionCommand


logger = get_logger(__file__)


class CommandStore(ESStorage, CommandBase):
    def __init__(self, params):
        super().__init__(params)

    def filter(self, date_from=None, date_to=None,
               user=None, asset=None, system_user=None,
               input=None, session=None, risk_level=None, org_id=None):

        if date_from is not None:
            if isinstance(date_from, float):
                date_from = datetime.fromtimestamp(date_from)
        if date_to is not None:
            if isinstance(date_to, float):
                date_to = datetime.fromtimestamp(date_to)

        try:
            data = super().filter(date_from=date_from, date_to=date_to,
                                  user=user, asset=asset, system_user=system_user,
                                  input=input, session=session,
                                  risk_level=risk_level, org_id=org_id)
        except Exception as e:
            logger.error(e, exc_info=True)
            return []
        else:
            return AbstractSessionCommand.from_multi_dict(
                [item["_source"] for item in data["hits"] if item]
            )

    def count(self, date_from=None, date_to=None, user=None, asset=None,
              system_user=None, input=None, session=None):
        try:
            count = super().count(
                date_from=date_from, date_to=date_to, user=user, asset=asset,
                system_user=system_user, input=input, session=session
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            return 0
        else:
            return count
