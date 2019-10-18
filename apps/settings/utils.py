# -*- coding: utf-8 -*-
#

from ldap3 import Server, Connection
from django.utils.translation import ugettext_lazy as _

from users.models import User
from users.utils import construct_user_email
from common.utils import get_logger
from common.const import LDAP_AD_ACCOUNT_DISABLE

from .models import settings


logger = get_logger(__file__)


class LDAPOUGroupException(Exception):
    pass


class LDAPUtil:
    _conn = None

    SEARCH_FIELD_ALL = 'all'
    SEARCH_FIELD_USERNAME = 'username'

    def __init__(self, use_settings_config=True, server_uri=None, bind_dn=None,
                 password=None, use_ssl=None, search_ougroup=None,
                 search_filter=None, attr_map=None, auth_ldap=None):
        # config
        self.paged_size = settings.AUTH_LDAP_SEARCH_PAGED_SIZE

        if use_settings_config:
            self._load_config_from_settings()
        else:
            self.server_uri = server_uri
            self.bind_dn = bind_dn
            self.password = password
            self.use_ssl = use_ssl
            self.search_ougroup = search_ougroup
            self.search_filter = search_filter
            self.attr_map = attr_map
            self.auth_ldap = auth_ldap

    def _load_config_from_settings(self):
        self.server_uri = settings.AUTH_LDAP_SERVER_URI
        self.bind_dn = settings.AUTH_LDAP_BIND_DN
        self.password = settings.AUTH_LDAP_BIND_PASSWORD
        self.use_ssl = settings.AUTH_LDAP_START_TLS
        self.search_ougroup = settings.AUTH_LDAP_SEARCH_OU
        self.search_filter = settings.AUTH_LDAP_SEARCH_FILTER
        self.attr_map = settings.AUTH_LDAP_USER_ATTR_MAP
        self.auth_ldap = settings.AUTH_LDAP

    @property
    def connection(self):
        if self._conn is None:
            server = Server(self.server_uri, use_ssl=self.use_ssl)
            conn = Connection(server, self.bind_dn, self.password)
            conn.bind()
            self._conn = conn
        return self._conn

    @staticmethod
    def get_user_by_username(username):
        try:
            user = User.objects.get(username=username)
        except Exception as e:
            return None
        else:
            return user

    def _ldap_entry_to_user_item(self, entry):
        user_item = {}
        for attr, mapping in self.attr_map.items():
            if not hasattr(entry, mapping):
                continue
            value = getattr(entry, mapping).value or ''
            if mapping.lower() == 'useraccountcontrol' and attr == 'is_active'\
                    and value:
                value = int(value) & LDAP_AD_ACCOUNT_DISABLE \
                        != LDAP_AD_ACCOUNT_DISABLE
            user_item[attr] = value
        return user_item

    def _search_user_items_ou(self, search_ou, extra_filter=None, cookie=None):
        search_filter = self.search_filter % {"user": "*"}
        if extra_filter:
            search_filter = '(&{}{})'.format(search_filter, extra_filter)

        ok = self.connection.search(
            search_ou, search_filter,
            attributes=list(self.attr_map.values()),
            paged_size=self.paged_size, paged_cookie=cookie
        )
        if not ok:
            error = _("Search no entry matched in ou {}".format(search_ou))
            raise LDAPOUGroupException(error)

        user_items = []
        for entry in self.connection.entries:
            user_item = self._ldap_entry_to_user_item(entry)
            user = self.get_user_by_username(user_item['username'])
            user_item['existing'] = bool(user)
            if user_item in user_items:
                continue
            user_items.append(user_item)
        return user_items

    def _cookie(self):
        if self.paged_size is None:
            cookie = None
        else:
            cookie = self.connection.result['controls']['1.2.840.113556.1.4.319']['value']['cookie']
        return cookie

    def search_user_items(self, extra_filter=None):
        user_items = []
        logger.info("Search user items")

        for search_ou in str(self.search_ougroup).split("|"):
            logger.info("Search user search ou: {}".format(search_ou))
            _user_items = self._search_user_items_ou(search_ou, extra_filter=extra_filter)
            user_items.extend(_user_items)
            while self._cookie():
                logger.info("Page Search user search ou: {}".format(search_ou))
                _user_items = self._search_user_items_ou(search_ou, extra_filter, self._cookie())
                user_items.extend(_user_items)
        logger.info("Search user items end")
        return user_items

    def construct_extra_filter(self, field, q):
        if not q:
            return None
        extra_filter = ''
        if field == self.SEARCH_FIELD_ALL:
            for attr in self.attr_map.values():
                extra_filter += '({}={})'.format(attr, q)
            extra_filter = '(|{})'.format(extra_filter)
            return extra_filter

        if field == self.SEARCH_FIELD_USERNAME and isinstance(q, list):
            attr = self.attr_map.get('username')
            for username in q:
                extra_filter += '({}={})'.format(attr, username)
            extra_filter = '(|{})'.format(extra_filter)
            return extra_filter

    def search_filter_user_items(self, username_list):
        extra_filter = self.construct_extra_filter(
            self.SEARCH_FIELD_USERNAME, username_list
        )
        user_items = self.search_user_items(extra_filter)
        return user_items

    @staticmethod
    def save_user(user, user_item):
        for field, value in user_item.items():
            if not hasattr(user, field):
                continue
            if isinstance(getattr(user, field), bool):
                if isinstance(value, str):
                    value = value.lower()
                value = value in ['true', 1, True]
            setattr(user, field, value)
        user.save()

    def update_user(self, user_item):
        user = self.get_user_by_username(user_item['username'])
        if user.source != User.SOURCE_LDAP:
            msg = _('The user source is not LDAP')
            return False, msg
        try:
            self.save_user(user, user_item)
        except Exception as e:
            logger.error(e, exc_info=True)
            return False, str(e)
        else:
            return True, None

    def create_user(self, user_item):
        user = User(source=User.SOURCE_LDAP)
        try:
            self.save_user(user, user_item)
        except Exception as e:
            logger.error(e, exc_info=True)
            return False, str(e)
        else:
            return True, None

    @staticmethod
    def construct_user_email(user_item):
        username = user_item['username']
        email = user_item.get('email', '')
        email = construct_user_email(username, email)
        return email

    def create_or_update_users(self, user_items):
        succeed = failed = 0
        for user_item in user_items:
            exist = user_item.pop('existing', False)
            user_item['email'] = self.construct_user_email(user_item)
            if not exist:
                ok, error = self.create_user(user_item)
            else:
                ok, error = self.update_user(user_item)
            if not ok:
                logger.info("Failed User: {}".format(user_item))
                failed += 1
            else:
                succeed += 1
        result = {'total': len(user_items), 'succeed': succeed, 'failed': failed}
        return result

    def sync_users(self, username_list=None):
        user_items = self.search_filter_user_items(username_list)
        result = self.create_or_update_users(user_items)
        return result
