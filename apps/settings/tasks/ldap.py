# coding: utf-8
# 

from celery import shared_task

from common.utils import get_logger
from ..utils import LDAPSyncUtil

__all__ = ['sync_ldap_user_task']


logger = get_logger(__file__)


@shared_task
def sync_ldap_user_task():
    LDAPSyncUtil().perform_sync()
