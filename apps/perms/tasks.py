# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from common.utils import get_logger, encrypt_password

logger = get_logger(__file__)



