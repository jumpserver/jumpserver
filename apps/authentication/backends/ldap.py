# coding:utf-8
#
import abc
import ldap
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django_auth_ldap.backend import _LDAPUser, LDAPBackend, valid_cache_key
from django_auth_ldap.config import _LDAPConfig, LDAPSearch, LDAPSearchUnion

from users.utils import construct_user_email
from common.const import LDAP_AD_ACCOUNT_DISABLE
from common.utils.http import is_true
from .base import JMSBaseAuthBackend

logger = _LDAPConfig.get_logger()


class LDAPBaseBackend(LDAPBackend):

    @abc.abstractmethod
    def is_enabled(self):
        raise NotImplementedError('is_enabled')

    @property
    @abc.abstractmethod
    def is_user_login_only_in_users(self):
        raise NotImplementedError('is_authenticated')

    def get_or_build_user(self, username, ldap_user):
        """
        This must return a (User, built) 2-tuple for the given LDAP user.

        username is the Django-friendly username of the user. ldap_user.dn is
        the user's DN and ldap_user.attrs contains all of their LDAP
        attributes.

        The returned User object may be an unsaved model instance.

        """
        model = self.get_user_model()

        if self.settings.USER_QUERY_FIELD:
            query_field = self.settings.USER_QUERY_FIELD
            query_value = ldap_user.attrs[self.settings.USER_ATTR_MAP[query_field]][0]
            query_value = query_value.strip()
            lookup = query_field
        else:
            query_field = model.USERNAME_FIELD
            query_value = username.lower()
            lookup = "{}__iexact".format(query_field)

        try:
            user = model.objects.get(**{lookup: query_value})
        except model.DoesNotExist:
            user = model(**{query_field: query_value})
            built = True
        else:
            built = False

        return user, built

    def get_user(self, user_id):
        user = None
        try:
            user = self.get_user_model().objects.get(pk=user_id)
            LDAPUser(self, user=user)  # This sets user.ldap_user
        except ObjectDoesNotExist:
            pass
        return user

    def get_group_permissions(self, user, obj=None):
        if not hasattr(user, 'ldap_user') and self.settings.AUTHORIZE_ALL_USERS:
            LDAPUser(self, user=user)  # This sets user.ldap_user
        if hasattr(user, 'ldap_user'):
            permissions = user.ldap_user.get_group_permissions()
        else:
            permissions = set()
        return permissions

    def populate_user(self, username):
        ldap_user = LDAPUser(self, username=username)
        user = ldap_user.populate_user()
        return user

    def authenticate(self, request=None, username=None, password=None, **kwargs):
        logger.info('Authentication LDAP backend')
        if username is None or password is None:
            logger.info('No username or password')
            return None
        match, msg = self.pre_check(username, password)
        if not match:
            logger.info('Authenticate failed: {}'.format(msg))
            return None
        ldap_user = LDAPUser(self, username=username.strip(), request=request)
        user = self.authenticate_ldap_user(ldap_user, password)
        logger.info('Authenticate user: {}'.format(user))
        return user if self.user_can_authenticate(user) else None

    def pre_check(self, username, password):
        if not self.is_enabled():
            error = 'Not enabled auth ldap'
            return False, error
        if not username:
            error = 'Username is None'
            return False, error
        if not password:
            error = 'Password is None'
            return False, error
        if self.is_user_login_only_in_users:
            user_model = self.get_user_model()
            exist = user_model.objects.filter(username=username).exists()
            if not exist:
                error = 'user ({}) is not in the user list'.format(username)
                return False, error
        return True, ''


class LDAPAuthorizationBackend(JMSBaseAuthBackend, LDAPBaseBackend):
    """
    Override this class to override _LDAPUser to LDAPUser
    """

    @staticmethod
    def is_enabled():
        return settings.AUTH_LDAP

    @property
    def is_user_login_only_in_users(self):
        return settings.AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS


class LDAPHAAuthorizationBackend(JMSBaseAuthBackend, LDAPBaseBackend):
    """
    Override this class to override _LDAPUser to LDAPUser
    """
    settings_prefix = "AUTH_LDAP_HA_"

    @staticmethod
    def is_enabled():
        return settings.AUTH_LDAP_HA

    @property
    def is_user_login_only_in_users(self):
        return settings.AUTH_LDAP_HA_USER_LOGIN_ONLY_IN_USERS


class LDAPUser(_LDAPUser):

    def __init__(self, backend, username=None, user=None, request=None):
        super().__init__(backend=backend, username=username, user=user, request=request)
        config_prefix = "" if isinstance(self.backend, LDAPAuthorizationBackend) else "_ha"
        self.user_dn_cache_key = valid_cache_key(
            f"django_auth_ldap{config_prefix}.user_dn.{self._username}"
        )
        self.category = f"ldap{config_prefix}"
        self.search_filter = getattr(settings, f"AUTH_LDAP{config_prefix.upper()}_SEARCH_FILTER", None)
        self.search_ou = getattr(settings, f"AUTH_LDAP{config_prefix.upper()}_SEARCH_OU", None)

    def _search_for_user_dn_from_ldap_util(self):
        from settings.utils import LDAPServerUtil
        util = LDAPServerUtil(category=self.category)
        user_dn = util.search_for_user_dn(self._username)
        return user_dn

    def _load_user_dn(self):
        """
        Populates self._user_dn with the distinguished name of our user.

        This will either construct the DN from a template in
        AUTH_LDAP_USER_DN_TEMPLATE or connect to the server and search for it.
        If we have to search, we'll cache the DN.

        """
        if self._using_simple_bind_mode():
            self._user_dn = self._construct_simple_user_dn()
        else:
            if self.settings.CACHE_TIMEOUT > 0:
                self._user_dn = cache.get_or_set(
                    self.user_dn_cache_key, self._search_for_user_dn, self.settings.CACHE_TIMEOUT
                )
            else:
                self._user_dn = self._search_for_user_dn()

    def _search_for_user_dn(self):
        """
        This method was overridden because the AUTH_LDAP_USER_SEARCH
        configuration in the settings.py file
        is configured with a `lambda` problem value
        """
        user_search_union = [
            LDAPSearch(
                USER_SEARCH, ldap.SCOPE_SUBTREE,
                self.search_filter
            )
            for USER_SEARCH in str(self.search_ou).split("|")
        ]

        search = LDAPSearchUnion(*user_search_union)
        if search is None:
            raise ImproperlyConfigured(
                'AUTH_LDAP_USER_SEARCH must be an LDAPSearch instance.'
            )

        results = search.execute(self.connection, {'user': self._username})
        if results is not None and len(results) == 1:
            (user_dn, self._user_attrs) = next(iter(results))
        else:
            # 解决直接配置DC域，用户认证失败的问题(库不能从整棵树中搜索)
            user_dn = self._search_for_user_dn_from_ldap_util()
            if user_dn is None:
                self._user_dn = None
                self._user_attrs = None
            else:
                self._user_dn = user_dn
                self._user_attrs = self._load_user_attrs()

        return user_dn

    def _populate_user_from_attributes(self):
        for field, attr in self.settings.USER_ATTR_MAP.items():
            if field in ['groups']:
                continue
            try:
                value = self.attrs[attr][0]
                value = value.strip()
                if field == 'is_active':
                    if attr.lower() == 'useraccountcontrol' and value:
                        value = int(value) & LDAP_AD_ACCOUNT_DISABLE != LDAP_AD_ACCOUNT_DISABLE
                    else:
                        value = is_true(value)
            except LookupError:
                logger.warning(
                    "{} does not have a value for the attribute {}".format(self.dn, attr))
            else:
                if not hasattr(self._user, field):
                    continue
                if isinstance(getattr(self._user, field), bool):
                    if isinstance(value, str):
                        value = value.lower()
                    value = value in ['true', '1', True]
                setattr(self._user, field, value)

        email = getattr(self._user, 'email', '')
        email = construct_user_email(self._user.username, email)
        setattr(self._user, 'email', email)
