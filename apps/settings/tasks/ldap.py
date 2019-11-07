# coding: utf-8
# 

from celery import shared_task
from ..utils import LDAPServerUtil, LDAPCacheUtil


__all__ = ['fetch_ldap_users_from_server_to_cache']


@shared_task
def fetch_ldap_users_from_server_to_cache():
    LDAPCacheUtil().refresh_users()
