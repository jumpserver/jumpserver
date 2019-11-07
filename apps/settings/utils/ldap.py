# coding: utf-8
#

from ldap3 import Server, Connection
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.cache import cache

from common.const import LDAP_AD_ACCOUNT_DISABLE
from common.utils import get_logger
from users.models import User
from users.utils import construct_user_email


logger = get_logger(__file__)

__all__ = ['LDAPServerUtil', 'LDAPCacheUtil', 'LDAPUtil', 'LDAPSyncUtil']


class LDAPOUGroupException(Exception):
    pass


class LDAPConfig(object):

    def __init__(self, config=None):
        self.server_uri = None
        self.bind_dn = None
        self.password = None
        self.use_ssl = None
        self.search_ougroup = None
        self.search_filter = None
        self.attr_map = None
        self.auth_ldap = None
        self.paged_size = None
        self.load(config)

    def load(self, config=None):
        self.paged_size = settings.AUTH_LDAP_SEARCH_PAGED_SIZE
        if config is None:
            self.load_from_settings()
        else:
            self.load_from_config(config)

    def load_from_config(self, config):
        self.server_uri = config.get('server_uri')
        self.bind_dn = config.get('bind_dn')
        self.password = config.get('password')
        self.use_ssl = config.get('use_ssl')
        self.search_ougroup = config.get('search_ougroup')
        self.search_filter = config.get('search_filter')
        self.attr_map = config.get('attr_map')
        self.auth_ldap = config.get('auth_ldap')

    def load_from_settings(self):
        self.server_uri = settings.AUTH_LDAP_SERVER_URI
        self.bind_dn = settings.AUTH_LDAP_BIND_DN
        self.password = settings.AUTH_LDAP_BIND_PASSWORD
        self.use_ssl = settings.AUTH_LDAP_START_TLS
        self.search_ougroup = settings.AUTH_LDAP_SEARCH_OU
        self.search_filter = settings.AUTH_LDAP_SEARCH_FILTER
        self.attr_map = settings.AUTH_LDAP_USER_ATTR_MAP
        self.auth_ldap = settings.AUTH_LDAP


class LDAPServerUtil(object):
    EXTRA_FILTER_FILED_USERNAME = 'username'
    EXTRA_FILTER_FILED_ALL = 'all'

    def __init__(self, config=None, username_list=None, search_value=None):
        self.config = LDAPConfig(config)
        self._conn = None
        self.filter_username_list = username_list
        self.filter_search_value = search_value

    @property
    def connection(self):
        if self._conn is None:
            server = Server(self.config.server_uri, use_ssl=self.config.use_ssl)
            conn = Connection(server, self.config.bind_dn, self.config.password)
            conn.bind()
            self._conn = conn
        return self._conn

    @property
    def paged_cookie(self):
        if self.config.paged_size is None:
            cookie = None
        else:
            cookie = self.connection.result['controls']['1.2.840.113556.1.4.319']['value']['cookie']
        return cookie

    def construct_extra_filter(self):
        extra_filter = ''
        if self.filter_username_list:
            username_mapping = self.config.attr_map.get('username')
            for username in self.filter_username_list:
                extra_filter += '({}={})'.format(username_mapping, username)
            extra_filter = '(|{})'.format(extra_filter)
            return extra_filter
        elif self.filter_search_value:
            for attr in self.config.attr_map.values():
                extra_filter += '{{}={}}'.format(attr, self.filter_search_value)
            extra_filter = '(|{})'.format(extra_filter)
            return extra_filter
        else:
            return None

    def get_search_filter(self):
        search_filter = self.config.search_filter % {'user': '*'}
        extra_filter = self.construct_extra_filter()
        if extra_filter:
            search_filter = '(&{}{})'.format(search_filter, extra_filter)
        return search_filter

    def search_user_entries_ou(self, search_ou, paged_cookie=None):
        logger.info("Search user entries ou: {}".format(search_ou))
        search_filter = self.get_search_filter()
        attributes = list(self.config.attr_map.values())
        paged_size = self.config.paged_size

        ok = self.connection.search(
            search_ou, search_filter, attributes=attributes,
            paged_size=paged_size, paged_cookie=paged_cookie
        )
        if not ok:
            error = _("Search no entry matched in ou {}".format(search_ou))
            raise LDAPOUGroupException(error)

    def search_user_entries(self):
        logger.info("Start search user entries")
        entries = []
        search_ou_list = str(self.config.search_ougroup).split('|')
        for search_ou in search_ou_list:
            self.search_user_entries_ou(search_ou)
            entries.extend(self.connection.entries)
            while self.paged_cookie:
                self.search_user_entries_ou(
                    search_ou, paged_cookie=self.paged_cookie
                )
                entries.extend(self.connection.entries)
        logger.info("Search user entries finished")
        return entries

    def user_entry_to_dict(self, entry):
        attr_map = self.config.attr_map.items()
        user_dict = {}
        for attr, mapping in attr_map:
            if not hasattr(entry, mapping):
                continue
            value = getattr(entry, mapping).value or ''
            if mapping.lower() == 'useraccountcontrol' \
                    and attr == 'is_active' \
                    and value:
                value = int(value) & LDAP_AD_ACCOUNT_DISABLE !=LDAP_AD_ACCOUNT_DISABLE
            user_dict[attr] = value
        return user_dict

    def get_users_format_dict(self):
        users_dict = []
        entries = self.search_user_entries()
        for entry in entries:
            user_dict = self.user_entry_to_dict(entry)
            users_dict.append(user_dict)
        return users_dict

    def test(self):
        entries = self.search_user_entries()
        return entries


class LDAPCacheUtil(object):
    CACHE_KEY_USERS = "CACHE_KEY_LDAP_USERS"

    def __init__(self,
                 config=None,
                 username_list=None,
                 search_value=None,
                 timeout=None):
        self.server_util = LDAPServerUtil(config=config)
        self.timeout = timeout
        self.username_list = username_list
        self.search_value = search_value

    def fetch_users(self):
        logger.info("Fetch users from server")
        users = self.server_util.get_users_format_dict()
        return users

    def set_users(self):
        logger.info("Set users to cache")
        users = self.fetch_users()
        cache.set(self.CACHE_KEY_USERS, users, self.timeout)
        return users

    def get_users(self):
        logger.info("Get users from cache")
        users = cache.get(self.CACHE_KEY_USERS, [])
        return users

    def delete_users(self):
        logger.info("Delete users of cache")
        cache.delete(self.CACHE_KEY_USERS)

    def refresh_users(self):
        logger.info("Start refresh users to cache")
        self.delete_users()
        self.set_users()
        logger.info("Refresh users to cache finished")

    def filter_users(self, users):
        if self.username_list:
            _users = []
            for user_dict in users:
                if user_dict['username'] not in self.username_list:
                    continue
                _users.append(user_dict)
            return _users
        elif self.search_value:
            _users = []
            for user_dict in users:
                user_dict_values_str = ','.join(user_dict.values())
                if self.search_value not in user_dict_values_str:
                    continue
                _users.append(user_dict)
            return _users
        else:
            return users

    def get_users_format_dict(self):
        users = self.get_users()
        # if not users:
        #     users = self.set_users()
        users = self.filter_users(users)
        return users


class LDAPUtil(object):

    def __init__(self,
                 use_cache=False,
                 ldap_config=None,
                 username_list=None,
                 search_value=None):

        self.use_cache = use_cache
        self.ldap_config = ldap_config
        self.username_list = username_list
        self.search_value = search_value
        self._util = None

    @property
    def util(self):
        if self._util:
            return self._util
        if self.use_cache:
            self._util = LDAPCacheUtil(
                config=self.ldap_config,
                username_list=self.username_list,
                search_value=self.search_value
            )
        else:
            self._util = LDAPServerUtil(
                config=self.ldap_config,
                username_list=self.username_list,
                search_value=self.search_value
            )
        return self._util

    @staticmethod
    def get_db_username_list():
        username_list = User.objects.all().values_list('username', flat=True)
        return username_list

    def get_users_format_dict(self):
        db_username_list = self.get_db_username_list()
        users_dict = self.util.get_users_format_dict()
        for user_dict in users_dict:
            # 前端data_table会根据row.id对table.selected值进行操作
            user_dict['id'] = user_dict['username']
            existing = user_dict['username'] in db_username_list
            user_dict['existing'] = existing
        return users_dict


class LDAPSyncUtil(object):

    def __init__(self,
                 use_cache=False,
                 ldap_config=None,
                 username_list=None,
                 search_value=None):
        self.util = LDAPUtil(
            use_cache=use_cache, ldap_config=ldap_config,
            username_list=username_list, search_value=search_value
        )

    @staticmethod
    def save_user(user, user_dict):
        for field, value in user_dict.items():
            if not hasattr(user, field):
                continue
            if isinstance(getattr(user, field), bool):
                if isinstance(value, str):
                    value = value.lower()
                value = value in ['true', 1, True]
            setattr(user, field, value)
        user.save()

    def create_user(self, user_dict):
        user = User(source=User.SOURCE_LDAP)
        try:
            self.save_user(user, user_dict)
        except Exception as e:
            logger.error(e, exc_info=True)
            return False, str(e)
        else:
            return True, None

    def update_user(self, user_dict):
        username = user_dict['username']
        user = User.objects.filter(username=username).first()
        if not user:
            msg = _('The user ({}) does not exist'.format(username))
            return False, msg
        if user.source != User.SOURCE_LDAP:
            msg = _('The user ({}) source ({}) is not LDAP'.format(username, user.source))
            return False, msg
        try:
            self.save_user(user, user_dict)
        except Exception as e:
            logger.error(e, exc_info=True)
            return False, str(e)
        else:
            return True, None

    @staticmethod
    def construct_user_email(user_dict):
        username = user_dict['username']
        email = user_dict.get('email', '')
        email = construct_user_email(username, email)
        return email

    def create_or_update_users(self, users_dict):
        succeed = failed = 0
        for user_dict in users_dict:
            user_dict.pop('id', None)
            existing = user_dict.pop('existing', False)
            user_dict['email'] = self.construct_user_email(user_dict)
            if existing:
                ok, error = self.update_user(user_dict)
            else:
                ok, error = self.create_user(user_dict)

            if ok:
                succeed += 1
            else:
                failed += 1
        result = {'total': len(users_dict), 'succeed': succeed, 'failed': failed}
        return result

    def get_users_format_dict(self):
        users_dict = self.util.get_users_format_dict()
        return users_dict

    def sync(self):
        users_dict = self.get_users_format_dict()
        result = self.create_or_update_users(users_dict)
        return result

