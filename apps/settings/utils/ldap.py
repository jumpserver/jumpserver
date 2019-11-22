# coding: utf-8
#

from ldap3 import Server, Connection
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from common.const import LDAP_AD_ACCOUNT_DISABLE
from common.utils import timeit, get_logger
from users.utils import construct_user_email
from users.models import User

logger = get_logger(__file__)

__all__ = [
    'LDAPConfig', 'LDAPServerUtil', 'LDAPCacheUtil', 'LDAPImportUtil',
    'LDAPSyncUtil', 'LDAP_USE_CACHE_FLAGS'
]

LDAP_USE_CACHE_FLAGS = [1, '1', 'true', 'True', True]


class LDAPConfig(object):

    def __init__(self, config=None):
        self.server_uri = None
        self.bind_dn = None
        self.password = None
        self.use_ssl = None
        self.search_ougroup = None
        self.search_filter = None
        self.attr_map = None
        if isinstance(config, dict):
            self.load_from_config(config)
        else:
            self.load_from_settings()

    def load_from_config(self, config):
        self.server_uri = config.get('server_uri')
        self.bind_dn = config.get('bind_dn')
        self.password = config.get('password')
        self.use_ssl = config.get('use_ssl')
        self.search_ougroup = config.get('search_ougroup')
        self.search_filter = config.get('search_filter')
        self.attr_map = config.get('attr_map')

    def load_from_settings(self):
        self.server_uri = settings.AUTH_LDAP_SERVER_URI
        self.bind_dn = settings.AUTH_LDAP_BIND_DN
        self.password = settings.AUTH_LDAP_BIND_PASSWORD
        self.use_ssl = settings.AUTH_LDAP_START_TLS
        self.search_ougroup = settings.AUTH_LDAP_SEARCH_OU
        self.search_filter = settings.AUTH_LDAP_SEARCH_FILTER
        self.attr_map = settings.AUTH_LDAP_USER_ATTR_MAP


class LDAPServerUtil(object):

    def __init__(self, config=None):
        if isinstance(config, dict):
            self.config = LDAPConfig(config=config)
        elif isinstance(config, LDAPConfig):
            self.config = config
        else:
            self.config = LDAPConfig()
        self._conn = None
        self._paged_size = self.get_paged_size()
        self.search_users = None
        self.search_value = None

    @property
    def connection(self):
        if self._conn:
            return self._conn
        server = Server(self.config.server_uri, use_ssl=self.config.use_ssl)
        conn = Connection(server, self.config.bind_dn, self.config.password)
        conn.bind()
        self._conn = conn
        return self._conn

    @staticmethod
    def get_paged_size():
        paged_size = settings.AUTH_LDAP_SEARCH_PAGED_SIZE
        if isinstance(paged_size, int):
            return paged_size
        return None

    def paged_cookie(self):
        if self._paged_size is None:
            return None
        try:
            cookie = self.connection.result['controls']['1.2.840.113556.1.4.319']['value']['cookie']
            return cookie
        except Exception as e:
            logger.error(e)
            return None

    def get_search_filter_extra(self):
        extra = ''
        if self.search_users:
            mapping_username = self.config.attr_map.get('username')
            for user in self.search_users:
                extra += '({}={})'.format(mapping_username, user)
            return '(|{})'.format(extra)
        if self.search_value:
            for attr in self.config.attr_map.values():
                extra += '({}={})'.format(attr, self.search_value)
            return '(|{})'.format(extra)
        return extra

    def get_search_filter(self):
        search_filter = self.config.search_filter % {'user': '*'}
        search_filter_extra = self.get_search_filter_extra()
        if search_filter_extra:
            search_filter = '(&{}{})'.format(search_filter, search_filter_extra)
        return search_filter

    def search_user_entries_ou(self, search_ou, paged_cookie=None):
        search_filter = self.get_search_filter()
        attributes = list(self.config.attr_map.values())
        self.connection.search(
            search_base=search_ou, search_filter=search_filter,
            attributes=attributes, paged_size=self._paged_size,
            paged_cookie=paged_cookie
        )

    @timeit
    def search_user_entries(self):
        logger.info("Search user entries")
        user_entries = list()
        search_ous = str(self.config.search_ougroup).split('|')
        for search_ou in search_ous:
            logger.info("Search user entries ou: {}".format(search_ou))
            self.search_user_entries_ou(search_ou)
            user_entries.extend(self.connection.entries)
            while self.paged_cookie():
                self.search_user_entries_ou(search_ou, self.paged_cookie())
                user_entries.extend(self.connection.entries)
        return user_entries

    def user_entry_to_dict(self, entry):
        user = {}
        attr_map = self.config.attr_map.items()
        for attr, mapping in attr_map:
            if not hasattr(entry, mapping):
                continue
            value = getattr(entry, mapping).value or ''
            if attr == 'is_active' and mapping.lower() == 'useraccountcontrol' \
                    and value:
                value = int(value) & LDAP_AD_ACCOUNT_DISABLE != LDAP_AD_ACCOUNT_DISABLE
            user[attr] = value
        return user

    @timeit
    def user_entries_to_dict(self, user_entries):
        users = []
        for user_entry in user_entries:
            user = self.user_entry_to_dict(user_entry)
            users.append(user)
        return users

    @timeit
    def search(self, search_users=None, search_value=None):
        logger.info("Search ldap users")
        self.search_users = search_users
        self.search_value = search_value
        user_entries = self.search_user_entries()
        users = self.user_entries_to_dict(user_entries)
        return users


class LDAPCacheUtil(object):
    CACHE_KEY_USERS = 'CACHE_KEY_LDAP_USERS'

    def __init__(self):
        self.search_users = None
        self.search_value = None

    def set_users(self, users):
        logger.info('Set ldap users to cache, count: {}'.format(len(users)))
        cache.set(self.CACHE_KEY_USERS, users, None)

    def get_users(self):
        users = cache.get(self.CACHE_KEY_USERS)
        count = users if users is None else len(users)
        logger.info('Get ldap users from cache, count: {}'.format(count))
        return users

    def delete_users(self):
        logger.info('Delete ldap users from cache')
        cache.delete(self.CACHE_KEY_USERS)

    def filter_users(self, users):
        if users is None:
            return users
        if self.search_users:
            filter_users = [
                user for user in users
                if user['username'] in self.search_users
            ]
        elif self.search_value:
            filter_users = [
                user for user in users
                if self.search_value in ','.join(user.values())
            ]
        else:
            filter_users = users
        return filter_users

    def search(self, search_users=None, search_value=None):
        self.search_users = search_users
        self.search_value = search_value
        users = self.get_users()
        users = self.filter_users(users)
        return users


class LDAPSyncUtil(object):
    CACHE_KEY_LDAP_USERS_SYNC_TASK_ERROR_MSG = 'CACHE_KEY_LDAP_USERS_SYNC_TASK_ERROR_MSG'

    CACHE_KEY_LDAP_USERS_SYNC_TASK_STATUS = 'CACHE_KEY_LDAP_USERS_SYNC_TASK_STATUS'
    TASK_STATUS_IS_RUNNING = 'RUNNING'
    TASK_STATUS_IS_OVER = 'OVER'

    def __init__(self):
        self.server_util = LDAPServerUtil()
        self.cache_util = LDAPCacheUtil()
        self.task_error_msg = None

    def clear_cache(self):
        logger.info('Clear ldap sync cache')
        self.delete_task_status()
        self.delete_task_error_msg()
        self.cache_util.delete_users()

    @property
    def task_no_start(self):
        status = self.get_task_status()
        return status is None

    @property
    def task_is_running(self):
        status = self.get_task_status()
        return status == self.TASK_STATUS_IS_RUNNING

    @property
    def task_is_over(self):
        status = self.get_task_status()
        return status == self.TASK_STATUS_IS_OVER

    def set_task_status(self, status):
        logger.info('Set task status: {}'.format(status))
        cache.set(self.CACHE_KEY_LDAP_USERS_SYNC_TASK_STATUS, status, None)

    def get_task_status(self):
        status = cache.get(self.CACHE_KEY_LDAP_USERS_SYNC_TASK_STATUS)
        logger.info('Get task status: {}'.format(status))
        return status

    def delete_task_status(self):
        logger.info('Delete task status')
        cache.delete(self.CACHE_KEY_LDAP_USERS_SYNC_TASK_STATUS)

    def set_task_error_msg(self, error_msg):
        logger.info('Set task error msg')
        cache.set(self.CACHE_KEY_LDAP_USERS_SYNC_TASK_ERROR_MSG, error_msg, None)

    def get_task_error_msg(self):
        logger.info('Get task error msg')
        error_msg = cache.get(self.CACHE_KEY_LDAP_USERS_SYNC_TASK_ERROR_MSG)
        return error_msg

    def delete_task_error_msg(self):
        logger.info('Delete task error msg')
        cache.delete(self.CACHE_KEY_LDAP_USERS_SYNC_TASK_ERROR_MSG)

    def pre_sync(self):
        self.set_task_status(self.TASK_STATUS_IS_RUNNING)

    def sync(self):
        users = self.server_util.search()
        self.cache_util.set_users(users)

    def post_sync(self):
        self.set_task_status(self.TASK_STATUS_IS_OVER)

    def perform_sync(self):
        logger.info('Start perform sync ldap users from server to cache')
        self.pre_sync()
        try:
            self.sync()
        except Exception as e:
            error_msg = str(e)
            logger.error(error_msg)
            self.set_task_error_msg(error_msg)
        self.post_sync()
        logger.info('End perform sync ldap users from server to cache')


class LDAPImportUtil(object):

    def __init__(self):
        pass

    @staticmethod
    def get_user_email(user):
        username = user['username']
        email = user['email']
        email = construct_user_email(username, email)
        return email

    def update_or_create(self, user):
        user['email'] = self.get_user_email(user)
        if user['username'] not in ['admin']:
            user['source'] = User.SOURCE_LDAP
        obj, created = User.objects.update_or_create(
            username=user['username'], defaults=user
        )
        return obj, created

    def perform_import(self, users):
        logger.info('Start perform import ldap users, count: {}'.format(len(users)))
        errors = []
        for user in users:
            try:
                self.update_or_create(user)
            except Exception as e:
                errors.append({user['username']: str(e)})
                logger.error(e)
        logger.info('End perform import ldap users')
        return errors



