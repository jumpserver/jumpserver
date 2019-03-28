# -*- coding: utf-8 -*-
#

from ldap3 import Server, Connection
from django.utils.translation import ugettext_lazy as _

from users.models import User
from common.utils import get_logger
from .models import settings


logger = get_logger(__file__)


class LDAPOUGroupException(Exception):
    pass


class LDAPUtil:

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

    @staticmethod
    def get_user_by_username(username):
        try:
            user = User.objects.get(username=username)
        except Exception as e:
            logger.info(e)
            return None
        else:
            return user

    @staticmethod
    def _update_user(user, user_item):
        for field, value in user_item.items():
            if not hasattr(user, field):
                continue
            setattr(user, field, value)
        user.save()

    def update_user(self, user_item):
        user = self.get_user_by_username(user_item['username'])
        if not user:
            msg = _('User does not exist')
            return False, msg
        if user.source != User.SOURCE_LDAP:
            msg = _('The user source is not LDAP')
            return False, msg

        try:
            self._update_user(user, user_item)
        except Exception as e:
            logger.error(e, exc_info=True)
            return False, str(e)
        else:
            return True, None

    @staticmethod
    def create_user(user_item):
        user_item['source'] = User.SOURCE_LDAP
        try:
            User.objects.create(**user_item)
        except Exception as e:
            logger.error(e, exc_info=True)
            return False, str(e)
        else:
            return True, None

    @staticmethod
    def get_or_construct_email(user_item):
        if not user_item.get('email', None):
            if '@' in user_item['username']:
                email = user_item['username']
            else:
                email = '{}@{}'.format(
                    user_item['username'], settings.EMAIL_SUFFIX)
        else:
            email = user_item['email']
        return email

    def create_or_update_users(self, user_items, force_update=True):
        succeed = failed = 0
        for user_item in user_items:
            user_item['email'] = self.get_or_construct_email(user_item)
            exist = user_item.pop('existing', None)
            if exist:
                ok, error = self.update_user(user_item)
            else:
                ok, error = self.create_user(user_item)
            if not ok:
                failed += 1
            else:
                succeed += 1
        result = {'total': len(user_items), 'succeed': succeed, 'failed': failed}
        return result

    def _ldap_entry_to_user_item(self, entry):
        user_item = {}
        for attr, mapping in self.attr_map.items():
            if not hasattr(entry, mapping):
                continue
            user_item[attr] = getattr(entry, mapping).value or ''
        return user_item

    def get_connection(self):
        server = Server(self.server_uri, use_ssl=self.use_ssl)
        conn = Connection(server, self.bind_dn, self.password)
        conn.bind()
        return conn

    def get_search_user_items(self):
        conn = self.get_connection()
        user_items = []
        search_ougroup = str(self.search_ougroup).split("|")
        for search_ou in search_ougroup:
            ok = conn.search(
                search_ou, self.search_filter % ({"user": "*"}),
                attributes=list(self.attr_map.values())
            )
            if not ok:
                error = _("Search no entry matched in ou {}".format(search_ou))
                raise LDAPOUGroupException(error)

            for entry in conn.entries:
                user_item = self._ldap_entry_to_user_item(entry)
                user = self.get_user_by_username(user_item['username'])
                user_item['existing'] = bool(user)
                user_items.append(user_item)

        return user_items

    def sync_users(self, username_set):
        user_items = self.get_search_user_items()
        if username_set:
            user_items = [u for u in user_items if u['username'] in username_set]
        result = self.create_or_update_users(user_items)
        return result
