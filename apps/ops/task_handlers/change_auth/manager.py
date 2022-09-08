# -*- coding: utf-8 -*-
#
from common.utils import get_logger
from ..base import BaseExecutionManager
from .handlers import ChangeAuthHandler

logger = get_logger(__name__)


class ChangeAuthExecutionManager(BaseExecutionManager):
    def get_handler_cls(self):
        return ChangeAuthHandler
