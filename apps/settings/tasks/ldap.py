# coding: utf-8
# 

from common.utils import get_logger
from ..utils import LDAPSyncUtil

__all__ = ['sync_ldap_user']


logger = get_logger(__file__)


def sync_ldap_user():
    LDAPSyncUtil().perform_sync()
