# -*- coding: utf-8 -*-
#

from ldap3 import Server, Connection
from django.utils.translation import ugettext_lazy as _

from users.models import User
from users.utils import construct_user_email
from common.utils import get_logger

from .models import settings


logger = get_logger(__file__)


class LDAPOUGroupException(Exception):
    pass


class LDAPUtil:
    _conn = None

    def __init__(self, use_settings_config=True, server_uri=None, bind_dn=None,
                 password=None, use_ssl=None, search_ougroup=None,
                 search_filter=None, attr_map=None, auth_ldap=None):
        # config
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
            user_item[attr] = getattr(entry, mapping).value or ''
        return user_item

    def search_user_items(self):
        user_items = []
        for search_ou in str(self.search_ougroup).split("|"):
            ok = self.connection.search(
                search_ou, self.search_filter % ({"user": "*"}),
                attributes=list(self.attr_map.values())
            )
            if not ok:
                error = _("Search no entry matched in ou {}".format(search_ou))
                raise LDAPOUGroupException(error)
            for entry in self.connection.entries:
                user_item = self._ldap_entry_to_user_item(entry)
                user = self.get_user_by_username(user_item['username'])
                user_item['existing'] = bool(user)
                user_items.append(user_item)
        return user_items

    def search_filter_user_items(self, username_list):
        user_items = self.search_user_items()
        if username_list:
            user_items = [u for u in user_items if u['username'] in username_list]
        return user_items

    @staticmethod
    def save_user(user, user_item):
        for field, value in user_item.items():
            if not hasattr(user, field):
                continue
            if isinstance(getattr(user, field), bool):
                value = value.lower() in ['true', 1]
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

    def create_or_update_users(self, user_items, force_update=True):
        succeed = failed = 0
        for user_item in user_items:
            exist = user_item.pop('existing', False)
            user_item['email'] = self.construct_user_email(user_item)
            if not exist:
                ok, error = self.create_user(user_item)
            else:
                ok, error = self.update_user(user_item)
            if not ok:
                failed += 1
            else:
                succeed += 1
        result = {'total': len(user_items), 'succeed': succeed, 'failed': failed}
        return result

    def sync_users(self, username_list):
        user_items = self.search_filter_user_items(username_list)
        result = self.create_or_update_users(user_items)
        return result
