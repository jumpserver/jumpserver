# coding: utf-8
#

import json
from collections import defaultdict
from copy import deepcopy

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from ldap import DECODING_ERROR
from ldap.dn import str2dn
from ldap3 import SIMPLE, Connection, Server, Tls
from ldap3.core.exceptions import (
    LDAPAttributeError,
    LDAPBindError,
    LDAPConfigurationError,
    LDAPExceptionError,
    LDAPInvalidDnError,
    LDAPInvalidFilterError,
    LDAPInvalidServerError,
    LDAPPasswordIsMandatoryError,
    LDAPSessionTerminatedByServerError,
    LDAPSocketOpenError,
    LDAPSocketReceiveError,
    LDAPUserNameIsMandatoryError,
)
from ldap3.utils.conv import escape_filter_chars

from authentication.mapping import (
    MISSING, AuthMappingError, AuthMappingService,
    normalize_auth_attributes, normalize_values,
)
from authentication.models import AuthRoleBinding
from common.const import LDAP_AD_ACCOUNT_DISABLE
from common.db.utils import close_old_connections
from common.utils import get_logger, timeit
from common.utils.http import is_true
from orgs.utils import tmp_to_org
from rbac.builtin import BuiltinRole
from rbac.const import Scope
from rbac.models import RoleBinding
from settings.const import ImportStatus
from settings.ldap_tls import LDAPTLSUtil
from users.models import User, UserGroup
from users.utils import construct_user_email

logger = get_logger(__file__)

__all__ = [
    'LDAPConfig', 'LDAPServerUtil', 'LDAPCacheUtil', 'LDAPImportUtil',
    'LDAPSyncUtil', 'LDAP_USE_CACHE_FLAGS', 'LDAPTestUtil',
]

LDAP_USE_CACHE_FLAGS = [1, '1', 'true', 'True', True]


class LDAPConfig(object):

    def __init__(self, config=None, category=User.Source.ldap.value):
        self.server_uri = None
        self.bind_dn = None
        self.password = None
        self.start_tls = None
        self.search_ou = None
        self.search_filter = None
        self.attr_map = None
        self.group_attribute = None
        self.group_search_ou = None
        self.group_search_filter = None
        self.group_search_user_attribute = None
        self.user_group_map = None
        self.user_role_map = None
        self.auth_ldap = None
        self.category = category
        if isinstance(config, dict):
            self.load_from_config(config)
        else:
            self.load_from_settings()

    def load_from_config(self, config):
        self.server_uri = config.get('server_uri')
        self.bind_dn = config.get('bind_dn')
        self.password = config.get('password')
        self.start_tls = config.get('start_tls', False)
        self.search_ou = config.get('search_ou')
        self.search_filter = config.get('search_filter')
        self.attr_map = config.get('attr_map')
        self.group_attribute = config.get('group_attribute') or ''
        self.group_search_ou = config.get('group_search_ou') or ''
        self.group_search_filter = config.get('group_search_filter') or ''
        self.group_search_user_attribute = (
            config.get('group_search_user_attribute') or ''
        )
        self.user_group_map = config.get('user_group_map') or []
        self.user_role_map = config.get('user_role_map') or []
        self.auth_ldap = config.get('auth_ldap')

    def load_from_settings(self):
        prefix = 'AUTH_LDAP' if self.category == User.Source.ldap.value else 'AUTH_LDAP_HA'
        self.server_uri = getattr(settings, f"{prefix}_SERVER_URI")
        self.bind_dn = getattr(settings, f"{prefix}_BIND_DN")
        self.password = getattr(settings, f"{prefix}_BIND_PASSWORD")
        self.start_tls = getattr(settings, f"{prefix}_START_TLS")
        self.search_ou = getattr(settings, f"{prefix}_SEARCH_OU")
        self.search_filter = getattr(settings, f"{prefix}_SEARCH_FILTER")
        self.attr_map = getattr(settings, f"{prefix}_USER_ATTR_MAP")
        self.group_attribute = getattr(settings, f"{prefix}_GROUP_ATTRIBUTE", '')
        self.group_search_ou = getattr(settings, f"{prefix}_GROUP_SEARCH_OU", '')
        self.group_search_filter = getattr(settings, f"{prefix}_GROUP_SEARCH_FILTER", '')
        self.group_search_user_attribute = getattr(
            settings, f"{prefix}_GROUP_SEARCH_USER_ATTRIBUTE", ''
        )
        self.user_group_map = getattr(settings, f"{prefix}_USER_GROUP_MAP", [])
        self.user_role_map = getattr(settings, f"{prefix}_USER_ROLE_MAP", [])
        self.auth_ldap = getattr(settings, prefix)

    @property
    def effective_group_attribute(self):
        if self.group_attribute:
            return self.group_attribute
        if isinstance(self.attr_map, dict):
            return self.attr_map.get('groups', '')
        return ''


class LDAPServerUtil(object):

    def __init__(self, config=None, category=User.Source.ldap.value):
        if isinstance(config, dict):
            self.config = LDAPConfig(config=config, category=category)
        elif isinstance(config, LDAPConfig):
            self.config = config
        else:
            self.config = LDAPConfig(category=category)
        self._conn = None
        self._paged_size = self.get_paged_size()
        self.search_users = None
        self.search_value = None
        self._tls_util = LDAPTLSUtil(self.config.category)

    def _get_tls(self):
        cert_paths = self._tls_util.get_cert_paths()
        if not cert_paths:
            return None
        tls_kwargs = {}
        if cert_paths.get('ca'):
            tls_kwargs['ca_certs_file'] = cert_paths['ca']
        if cert_paths.get('cert'):
            tls_kwargs['local_certificate_file'] = cert_paths['cert']
        if cert_paths.get('key'):
            tls_kwargs['local_private_key_file'] = cert_paths['key']
        return Tls(**tls_kwargs) if tls_kwargs else None

    def _open_connection(self, bind=False, user=None, password=None, authentication=None):
        server_uri = self.config.server_uri or ''
        use_ldaps = server_uri.lower().startswith('ldaps://')
        tls = self._get_tls()
        server = Server(server_uri, use_ssl=use_ldaps, tls=tls)
        conn = Connection(
            server, user=user or self.config.bind_dn,
            password=password if password is not None else self.config.password,
            authentication=authentication
        )
        conn.open(read_server_info=False)
        if not use_ldaps and self.config.start_tls:
            conn.start_tls()
        if bind:
            conn.bind()
        return conn

    def _create_connection(self):
        return self._open_connection(bind=True)

    @property
    def connection(self):
        if self._conn is not None:
            return self._conn
        self._conn = self._create_connection()
        return self._conn

    def close(self):
        connection = self._conn
        self._conn = None
        if connection is None:
            return
        unbind = getattr(connection, 'unbind', None)
        if not callable(unbind):
            return
        try:
            unbind()
        except Exception as error:
            logger.debug('Close LDAP connection failed: %s', error)

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
            logger.debug(e, exc_info=True)
            return None

    def get_search_filter_extra(self):
        extra = ''
        if self.search_users:
            mapping_username = self.config.attr_map.get('username')
            for user in self.search_users:
                extra += '({}={})'.format(
                    mapping_username, escape_filter_chars(user)
                )
            return '(|{})'.format(extra)
        if self.search_value:
            escaped_search_value = escape_filter_chars(self.search_value)
            for key, attr in self.config.attr_map.items():
                if key == 'groups':
                    continue
                extra += '({}={})'.format(attr, '*{}*'.format(escaped_search_value))
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
        attributes = self.get_user_search_attributes()
        ok = self.connection.search(
            search_base=search_ou, search_filter=search_filter,
            attributes=attributes, paged_size=self._paged_size,
            paged_cookie=paged_cookie
        )
        self.ensure_search_succeeded(ok, 'user search')

    def ensure_search_succeeded(self, ok, operation):
        result = self.connection.result or {}
        result_code = result.get('result')
        if ok is not False and result_code in (None, 0):
            return
        detail = (
            result.get('description') or result.get('message') or result_code
        )
        raise RuntimeError(f'LDAP {operation} failed: {detail}')

    def get_user_search_attributes(self):
        attr_map = self.config.attr_map
        if not isinstance(attr_map, dict):
            return []
        attributes = [value for key, value in attr_map.items() if key != 'groups']
        if self.config.group_search_filter:
            search_user_attr = (
                self.config.group_search_user_attribute or attr_map.get('username')
            )
            if search_user_attr and search_user_attr.lower() != 'dn':
                attributes.append(search_user_attr)
        elif self.config.effective_group_attribute:
            attributes.append(self.config.effective_group_attribute)
        for rule in self.config.user_role_map:
            attribute = rule.get('attribute', '')
            if attribute and attribute.casefold() not in ('dn', 'groups'):
                attributes.append(attribute)
        distinct = []
        seen = set()
        for attribute in attributes:
            key = attribute.casefold()
            if key == 'dn':
                continue
            if key in seen:
                continue
            seen.add(key)
            distinct.append(attribute)
        return distinct

    @staticmethod
    def distinct_user_entries(user_entries):
        distinct_user_entries = list()
        distinct_user_entries_dn = set()
        for user_entry in user_entries:
            if user_entry.entry_dn in distinct_user_entries_dn:
                continue
            distinct_user_entries_dn.add(user_entry.entry_dn)
            distinct_user_entries.append(user_entry)
        return distinct_user_entries

    @timeit
    def search_user_entries(self, search_users=None, search_value=None):
        logger.info("Search user entries")
        self.search_users = search_users
        self.search_value = search_value
        user_entries = list()
        search_ous = str(self.config.search_ou).split('|')
        for search_ou in search_ous:
            search_ou = search_ou.strip()
            logger.info("Search user entries ou: {}".format(search_ou))
            self.search_user_entries_ou(search_ou)
            user_entries.extend(self.connection.entries)
            while self.paged_cookie():
                self.search_user_entries_ou(search_ou, self.paged_cookie())
                user_entries.extend(self.connection.entries)
        user_entries = self.distinct_user_entries(user_entries)
        return user_entries

    @staticmethod
    def get_entry_values(entry, attribute):
        if attribute.lower() == 'dn':
            value = getattr(entry, 'entry_dn', None)
            return value is not None, [] if value is None else [value]
        try:
            entry_attribute = entry[attribute]
        except (AttributeError, KeyError, TypeError, LDAPAttributeError):
            try:
                entry_attribute = getattr(entry, attribute)
            except (AttributeError, LDAPAttributeError):
                return False, []
        values = getattr(entry_attribute, 'values', None)
        if values is None:
            values = getattr(entry_attribute, 'value', entry_attribute)
        if values is None:
            return True, []
        if isinstance(values, (list, tuple, set)):
            return True, list(values)
        return True, [values]

    def entry_to_auth_attributes(self, entry):
        attributes = {}
        for attribute in self.get_user_search_attributes():
            found, values = self.get_entry_values(entry, attribute)
            if found:
                attributes[attribute] = values
        return normalize_auth_attributes(
            attributes, dn=getattr(entry, 'entry_dn', '')
        )

    def get_group_search_user_value(self, attributes):
        attribute = self.config.group_search_user_attribute
        if not attribute:
            attribute = self.config.attr_map.get('username')
        values = attributes.get(attribute.casefold(), [])
        if not values:
            return None
        return values[0]

    def search_group_dns(self, user_value):
        if user_value in (None, ''):
            raise ValueError('LDAP group search user attribute is unavailable')
        search_filter = self.config.group_search_filter % escape_filter_chars(
            user_value
        )
        search_ou = self.config.group_search_ou or self.config.search_ou
        group_entries = []
        for group_search_ou in str(search_ou).split('|'):
            group_search_ou = group_search_ou.strip()
            ok = self.connection.search(
                search_base=group_search_ou,
                search_filter=search_filter,
                attributes=[],
                paged_size=self._paged_size,
            )
            self.ensure_group_search_succeeded(ok)
            group_entries.extend(self.connection.entries)
            while self.paged_cookie():
                ok = self.connection.search(
                    search_base=group_search_ou,
                    search_filter=search_filter,
                    attributes=[],
                    paged_size=self._paged_size,
                    paged_cookie=self.paged_cookie(),
                )
                self.ensure_group_search_succeeded(ok)
                group_entries.extend(self.connection.entries)
        group_dns = []
        seen = set()
        for group_entry in group_entries:
            group_dn = normalize_values(getattr(group_entry, 'entry_dn', ''))
            if not group_dn:
                continue
            group_dn = group_dn[0]
            key = group_dn.casefold()
            if key in seen:
                continue
            seen.add(key)
            group_dns.append(group_dn)
        return group_dns

    def ensure_group_search_succeeded(self, ok):
        self.ensure_search_succeeded(ok, 'group search')

    @staticmethod
    def normalize_group_values(values):
        groups = []
        seen = set()
        for value in normalize_values(values):
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            groups.append(value)
        return groups

    def get_groups(self, auth_attributes):
        if self.config.group_search_filter:
            user_value = self.get_group_search_user_value(auth_attributes)
            return self.search_group_dns(user_value)
        group_attribute = self.config.effective_group_attribute
        if group_attribute:
            values = auth_attributes.get(group_attribute.casefold(), [])
            return self.normalize_group_values(values)
        return MISSING

    def user_entry_to_dict(self, entry):
        user = {}
        auth_attributes = self.entry_to_auth_attributes(entry)
        for attr, mapping in self.config.attr_map.items():
            if attr == 'groups':
                continue
            values = auth_attributes.get(mapping.casefold())
            if values is None:
                continue
            value = values[0] if values else ''
            if attr == 'is_active':
                if mapping.lower() == 'useraccountcontrol' and value:
                    value = int(value) & LDAP_AD_ACCOUNT_DISABLE != LDAP_AD_ACCOUNT_DISABLE
                else:
                    value = is_true(value)
            user[attr] = value.strip() if isinstance(value, str) else value
        groups = self.get_groups(auth_attributes)
        if groups is not MISSING:
            user['groups'] = groups
            auth_attributes['groups'] = groups
        user['_auth_attributes'] = auth_attributes
        user['status'] = ImportStatus.pending
        return user

    def user_entries_to_dict(self, user_entries):
        users = []
        for user_entry in user_entries:
            try:
                user = self.user_entry_to_dict(user_entry)
            except Exception as error:
                username = self.get_entry_username(user_entry)
                user = {
                    'username': username,
                    'name': '',
                    'email': '',
                    '_auth_mapping_error': str(error),
                    'status': {'error': str(error)},
                }
            users.append(user)
        return users

    def get_entry_username(self, entry):
        attribute = self.config.attr_map.get('username')
        found, values = self.get_entry_values(entry, attribute)
        values = normalize_values(values) if found else []
        if not values:
            raise ValueError('LDAP username attribute is unavailable')
        return values[0]

    def search_for_user_dn(self, username):
        try:
            user_entries = self.search_user_entries(search_users=[username])
            if len(user_entries) == 1:
                user_entry = user_entries[0]
                return user_entry.entry_dn
            return None
        finally:
            self.close()

    @timeit
    def search(self, search_users=None, search_value=None):
        logger.info("Search ldap users")
        try:
            user_entries = self.search_user_entries(
                search_users=search_users, search_value=search_value
            )
            return self.user_entries_to_dict(user_entries)
        finally:
            self.close()


class LDAPCacheUtil(object):

    def __init__(self, category=User.Source.ldap.value):
        self.search_users = None
        self.search_value = None
        self.category = category
        self.cache_key_users = 'CACHE_KEY_{}_USERS'.format(self.category.upper())

    def set_users(self, users):
        logger.info('Set ldap users to cache, count: {}'.format(len(users)))
        cache.set(self.cache_key_users, users, None)

    def get_users(self):
        users = cache.get(self.cache_key_users)
        count = users if users is None else len(users)
        logger.info('Get ldap users from cache, count: {}'.format(count))
        return users

    def delete_users(self):
        logger.info('Delete ldap users from cache')
        cache.delete(self.cache_key_users)

    def filter_users(self, users):
        if users is None:
            return users
        if self.search_users:
            filter_users = [
                user for user in users
                if user['username'] in self.search_users
            ]
        elif self.search_value:
            filter_users = []
            for u in users:
                search_value = self.search_value.lower()
                user_all_attr_value = [v for v in u.values() if isinstance(v, str)]
                if search_value not in ','.join(user_all_attr_value).lower():
                    continue
                filter_users.append(u)
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
    class LDAPSyncUtilException(Exception):
        pass

    CACHE_KEY_LDAP_USERS_SYNC_TASK_ERROR_MSG = 'CACHE_KEY_LDAP_USERS_SYNC_TASK_ERROR_MSG'

    CACHE_KEY_LDAP_USERS_SYNC_TASK_STATUS = 'CACHE_KEY_LDAP_USERS_SYNC_TASK_STATUS'
    TASK_STATUS_IS_RUNNING = 'RUNNING'
    TASK_STATUS_IS_OVER = 'OVER'

    def __init__(self, category=User.Source.ldap.value):
        self.server_util = LDAPServerUtil(category=category)
        self.cache_util = LDAPCacheUtil(category=category)
        self.task_error_msg = None
        self.category = category

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
        error_msg = cache.get(self.CACHE_KEY_LDAP_USERS_SYNC_TASK_ERROR_MSG, '')
        return error_msg

    def delete_task_error_msg(self):
        logger.info('Delete task error msg')
        cache.delete(self.CACHE_KEY_LDAP_USERS_SYNC_TASK_ERROR_MSG)

    def sync(self):
        users = self.server_util.search()
        self.cache_util.set_users(users)

    def perform_sync(self):
        logger.info('Start perform sync ldap users from server to cache')
        try:
            ok, msg = LDAPTestUtil(category=self.category).test_config()
            if not ok:
                raise self.LDAPSyncUtilException(msg)
            self.sync()
        except Exception as e:
            error_msg = str(e)
            logger.error(error_msg)
            self.set_task_error_msg(error_msg)
        finally:
            logger.info('End perform sync ldap users from server to cache')
            close_old_connections()


class LDAPImportUtil(object):
    user_group_name_prefix = 'AD '

    def __init__(self, category=User.Source.ldap.value, is_sync_all=True):
        self.category = category
        self.is_sync_all = is_sync_all

    @staticmethod
    def get_user_email(user):
        username = user['username']
        email = user['email']
        email = construct_user_email(username, email)
        return email

    def update_or_create(self, user):
        user['email'] = self.get_user_email(user)
        if user['username'] not in ['admin']:
            user['source'] = self.category
        user.pop('status', None)
        obj, created = User.objects.update_or_create(
            username=user['username'], defaults=user
        )
        return obj, created

    def get_user_group_names(self, groups) -> list:
        if not isinstance(groups, list):
            raise TypeError('Groups type is not list')
        group_names = []
        seen = set()
        max_length = UserGroup._meta.get_field('name').max_length
        for group in groups:
            if not group:
                continue
            if not isinstance(group, str):
                raise TypeError('Group DN type is not string')
            # get group name for AD, Such as: CN=Users,CN=Builtin,DC=jms,DC=com
            try:
                rdns = str2dn(group)
            except DECODING_ERROR:
                group_name = group
            else:
                if not rdns or not rdns[0]:
                    continue
                group_name = rdns[0][0][1]
            group_name = f'{self.user_group_name_prefix}{group_name}'.strip()
            if len(group_name) > max_length:
                raise ValueError(
                    f'User group name exceeds {max_length} characters: {group_name}'
                )
            key = group_name.casefold()
            if key in seen:
                continue
            seen.add(key)
            group_names.append(group_name)
        return group_names

    def get_mapping_service(self):
        if self.category != User.Source.ldap.value:
            return None
        return AuthMappingService(
            source=self.category,
            group_rules=getattr(settings, 'AUTH_LDAP_USER_GROUP_MAP', []),
            role_rules=getattr(settings, 'AUTH_LDAP_USER_ROLE_MAP', []),
        )

    def perform_import(self, users, orgs):
        logger.info('Start perform import ldap users, count: {}'.format(len(users)))
        errors = []
        new_users = []
        group_users_mapper = defaultdict(set)
        group_sync_users = set()
        mapping_service = self.get_mapping_service()
        explicit_group_mapping = bool(
            getattr(settings, 'AUTH_LDAP_USER_GROUP_MAP', [])
        ) if mapping_service else False
        for user in users:
            mapping_error = user.pop('_auth_mapping_error', None)
            if mapping_error:
                errors.append({user['username']: mapping_error})
                logger.error(mapping_error)
                continue
            groups = user.pop('groups', MISSING)
            auth_attributes = user.pop('_auth_attributes', MISSING)
            try:
                obj, created = self.update_or_create(user)
                if created:
                    new_users.append(obj)
            except Exception as e:
                errors.append({user['username']: str(e)})
                logger.error(e)
                continue
            self.bind_user_orgs(obj, orgs)
            if mapping_service:
                try:
                    mapping_service.sync(
                        obj,
                        attributes=auth_attributes,
                        groups=groups,
                        raise_errors=True,
                    )
                except AuthMappingError as error:
                    errors.append({user['username']: str(error)})
                    logger.error(error)
                    continue
            if explicit_group_mapping or groups is MISSING:
                continue
            try:
                group_names = self.get_user_group_names(groups)
                group_sync_users.add(obj)
                for group_name in group_names:
                    group_users_mapper[group_name].add(obj)
            except Exception as e:
                errors.append({user['username']: str(e)})
                logger.error(e)
                continue
        for org in orgs:
            self.bind_org(org, group_users_mapper, group_sync_users)
        logger.info('End perform import ldap users')
        # 禁止ldap 不存在的用户的
        disable_usernames = []
        if self.strict_sync_enabled and self.is_sync_all:
            disable_usernames = self.disable_not_exist_users(users)

        if errors:
            logger.error(f"Imported {self.category.upper()} users errors: {errors}")
        else:
            logger.info(f"Imported {len(users)} {self.category.upper()} users successfully")
        return new_users, errors, disable_usernames

    @property
    def strict_sync_enabled(self):
        return getattr(settings, 'AUTH_{}_STRICT_SYNC'.format(self.category.upper()), False)

    def disable_not_exist_users(self, users):
        ldap_users = [user['username'] for user in users]
        disable_users = User.objects.filter(source=self.category, is_active=True).exclude(username__in=ldap_users).all()
        disable_usernames = disable_users.values_list('username', flat=True)
        disable_usernames = list(map(str, disable_usernames))
        disable_users.update(is_active=False)
        logger.info(f"Disable {len(disable_usernames)} {self.category.upper()} users successfully")
        return disable_usernames

    def exit_user_group(self, user_groups_mapper):
        # 通过对比查询本次导入用户需要移除的用户组
        group_remove_users_mapper = defaultdict(set)
        for user, current_groups in user_groups_mapper.items():
            old_groups = set(user.groups.filter(name__startswith=self.user_group_name_prefix))
            exit_groups = old_groups - current_groups
            logger.debug(f'Ldap user {user} exits user groups {exit_groups}')
            for g in exit_groups:
                group_remove_users_mapper[g].add(user)

        # 根据用户组统一移除用户
        for g, rm_users in group_remove_users_mapper.items():
            g.users.remove(*rm_users)

    def bind_user_orgs(self, user, orgs):
        for org in orgs:
            if not org or org.is_root():
                continue
            org.add_member(user)
            role_binding = RoleBinding.objects_raw.filter(
                user=user,
                role_id=BuiltinRole.org_user.id,
                org_id=org.id,
                scope=Scope.org,
            ).first()
            if role_binding:
                AuthRoleBinding.objects.filter(
                    source=self.category,
                    role_binding=role_binding,
                    owned=True,
                ).update(owned=False)

    def bind_org(self, org, group_users_mapper, group_sync_users):
        if not org:
            return
        if org.is_root():
            return
        # add user to group
        with tmp_to_org(org):
            user_groups_mapper = defaultdict(set)
            for user in group_sync_users:
                user_groups_mapper[user]
            for group_name, users in group_users_mapper.items():
                group, created = UserGroup.objects.get_or_create(
                    name=group_name, defaults={'name': group_name}
                )
                for user in users:
                    user_groups_mapper[user].add(group)
                group.users.add(*users)
            self.exit_user_group(user_groups_mapper)


class LDAPTestUtil(object):
    class LDAPInvalidSearchOuOrFilterError(LDAPExceptionError):
        pass

    class LDAPInvalidAttributeMapError(LDAPExceptionError):
        pass

    class LDAPNotEnabledAuthError(LDAPExceptionError):
        pass

    class LDAPBeforeLoginCheckError(LDAPExceptionError):
        pass

    def __init__(self, config=None, category=User.Source.ldap.value):
        from authentication.backends.ldap import (
            LDAPAuthorizationBackend, LDAPHAAuthorizationBackend,
        )
        if isinstance(config, dict):
            self._apply_test_tls_content(config, category)
        self.config = LDAPConfig(config, category)
        self.user_entries = []
        if category == User.Source.ldap.value:
            self.backend = LDAPAuthorizationBackend()
        else:
            self.backend = LDAPHAAuthorizationBackend()

    @staticmethod
    def _apply_test_tls_content(config, category):
        prefix = 'AUTH_LDAP' if category == User.Source.ldap.value else 'AUTH_LDAP_HA'
        content_map = {}
        mapping = {
            'cacert_content': f'{prefix}_CACERT_CONTENT',
            'cert_content': f'{prefix}_CERT_CONTENT',
            'key_content': f'{prefix}_KEY_CONTENT',
        }
        for config_key, attr in mapping.items():
            value = config.get(config_key)
            if value:
                content_map[attr] = value
        if content_map:
            LDAPTLSUtil(category).sync_files(content_map=content_map)

    def _test_connection_bind(self, authentication=None, user=None, password=None):
        util = LDAPServerUtil(config=self.config)
        connection = util._open_connection(
            bind=True, user=user, password=password, authentication=authentication
        )
        return connection.bound

    # test server uri

    def _check_server_uri(self):
        if not (self.config.server_uri.startswith('ldap://') or
                self.config.server_uri.startswith('ldaps://')):
            err = _('ldap:// or ldaps:// protocol is used.')
            raise LDAPInvalidServerError(err)

    def _test_server_uri(self):
        # 这里测试 server uri 是否能连通, 不进行 bind 操作, 不需要传入 bind dn 和密码
        util = LDAPServerUtil(config=self.config)
        connection = util._open_connection(bind=False)
        connection.unbind()

    def test_server_uri(self):
        try:
            self._check_server_uri()
            self._test_server_uri()
        except LDAPSocketOpenError as e:
            error = _("Host or port is disconnected: {}").format(e)
        except LDAPSessionTerminatedByServerError as e:
            error = _('The port is not the port of the LDAP service: {}').format(e)
        except LDAPSocketReceiveError as e:
            error = _('Please add certificate: {}').format(e)
        except LDAPInvalidServerError as e:
            error = str(e)
        except Exception as e:
            error = _('Unknown error: {}').format(e)
        else:
            return
        raise LDAPInvalidServerError(error)

    # test bind dn

    def _test_bind_dn(self):
        user = self.config.bind_dn
        password = self.config.password
        ret = self._test_connection_bind(
            authentication=SIMPLE, user=user, password=password
        )
        if not ret:
            msg = _('Bind DN or Password incorrect')
            raise LDAPInvalidDnError(msg)

    def test_bind_dn(self):
        try:
            self._test_bind_dn()
        except LDAPUserNameIsMandatoryError as e:
            error = _('Please enter Bind DN: {}').format(e)
        except LDAPPasswordIsMandatoryError as e:
            error = _('Please enter Password: {}').format(e)
        except LDAPInvalidDnError as e:
            error = _('Please enter correct Bind DN and Password: {}').format(e)
        except Exception as e:
            error = _('Unknown error: {}').format(e)
        else:
            return
        raise LDAPBindError(error)

    # test search ou

    def _test_search_ou_and_filter(self):
        config = deepcopy(self.config)
        util = LDAPServerUtil(config=config)
        try:
            search_ous = str(self.config.search_ou).split('|')
            for search_ou in search_ous:
                util.config.search_ou = search_ou
                user_entries = util.search_user_entries()
                logger.debug(
                    'Search ou: {}, count user: {}'.format(
                        search_ou, len(user_entries)
                    )
                )
                if len(user_entries) == 0:
                    error = _(
                        'Invalid User OU or User search filter: {}'
                    ).format(search_ou)
                    raise self.LDAPInvalidSearchOuOrFilterError(error)
        finally:
            util.close()

    def test_search_ou_and_filter(self):
        try:
            self._test_search_ou_and_filter()
        except LDAPInvalidFilterError as e:
            error = e
        except self.LDAPInvalidSearchOuOrFilterError as e:
            error = e
        except LDAPAttributeError as e:
            error = e
            raise self.LDAPInvalidAttributeMapError(error)
        except Exception as e:
            error = _('Unknown error: {}').format(e)
        else:
            return
        raise self.LDAPInvalidSearchOuOrFilterError(error)

    # test attr map

    def _test_attr_map(self):
        attr_map = self.config.attr_map
        if not isinstance(attr_map, dict):
            attr_map = json.loads(attr_map)
            self.config.attr_map = attr_map

        should_contain_attr = {'username', 'name', 'email'}
        actually_contain_attr = set(attr_map.keys())
        result = should_contain_attr - actually_contain_attr
        if len(result) != 0:
            error = _('LDAP User attr map not include: {}').format(result)
            raise self.LDAPInvalidAttributeMapError(error)

    def test_attr_map(self):
        try:
            self._test_attr_map()
        except json.JSONDecodeError:
            error = _('LDAP User attr map is not dict')
        except self.LDAPInvalidAttributeMapError as e:
            error = e
        except Exception as e:
            error = _('Unknown error: {}').format(e)
        else:
            return
        raise self.LDAPInvalidAttributeMapError(error)

    # test search

    def test_search(self):
        util = LDAPServerUtil(config=self.config)
        try:
            self.user_entries = util.search_user_entries()
            users = util.user_entries_to_dict(self.user_entries[:1])
            errors = [
                user['_auth_mapping_error'] for user in users
                if '_auth_mapping_error' in user
            ]
            if errors:
                raise ValueError(errors[0])
        finally:
            util.close()

    # test auth ldap enabled

    def test_enabled_auth_ldap(self):
        if not self.config.auth_ldap:
            error = _('LDAP authentication is not enabled')
            raise self.LDAPNotEnabledAuthError(error)

    # test config

    def _test_config(self):
        self.test_server_uri()
        self.test_bind_dn()
        self.test_attr_map()
        self.test_search_ou_and_filter()
        self.test_search()
        self.test_enabled_auth_ldap()

    def test_config(self):
        status = False
        try:
            self._test_config()
        except LDAPInvalidServerError as e:
            raise e
            msg = _('Error (Invalid LDAP server): {}').format(e)
        except LDAPBindError as e:
            msg = _('Error (Invalid Bind DN): {}').format(e)
        except self.LDAPInvalidAttributeMapError as e:
            msg = _('Error (Invalid LDAP User attr map): {}').format(e)
        except self.LDAPInvalidSearchOuOrFilterError as e:
            msg = _('Error (Invalid User OU or User search filter): {}').format(e)
        except self.LDAPNotEnabledAuthError as e:
            msg = _('Error (Not enabled LDAP authentication): {}').format(e)
        except Exception as e:
            msg = _('Error (Unknown): {}').format(e)
        else:
            status = True
            msg = _('Succeed: Match {} users').format(len(self.user_entries))

        if not status:
            logger.error(msg, exc_info=True)
        return status, msg

    # test login

    def _test_before_login_check(self, username, password):
        from settings.ws import CACHE_KEY_LDAP_TEST_CONFIG_TASK_STATUS
        if not cache.get(CACHE_KEY_LDAP_TEST_CONFIG_TASK_STATUS):
            self.test_config()

        ok, msg = self.backend.pre_check(username, password)
        if not ok:
            raise self.LDAPBeforeLoginCheckError(msg)

    def _test_login_auth(self, username, password):
        from authentication.backends.ldap import LDAPUser
        ldap_user = LDAPUser(self.backend, username=username.strip())
        ldap_user._authenticate_user_dn(password)

    def _test_login(self, username, password):
        self._test_before_login_check(username, password)
        self._test_login_auth(username, password)

    def test_login(self, username, password):
        from authentication.backends.ldap import LDAPUser
        status = False
        try:
            self._test_login(username, password)
        except LDAPConfigurationError as e:
            msg = _('Authentication failed (configuration incorrect): {}').format(e)
        except self.LDAPBeforeLoginCheckError as e:
            msg = _('Authentication failed (before login check failed): {}').format(e)
        except LDAPUser.AuthenticationFailed as e:
            msg = _('Authentication failed (username or password incorrect): {}').format(e)
        except Exception as e:
            msg = _("Authentication failed (Unknown): {}").format(e)
        else:
            status = True
            msg = _("Authentication success: {}").format(username)

        if not status:
            logger.error(msg, exc_info=True)
        return status, msg
