# coding:utf-8
#

import ldap
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django_auth_ldap.backend import _LDAPUser, LDAPBackend
from django_auth_ldap.config import _LDAPConfig, LDAPSearch, LDAPSearchUnion

from users.utils import construct_user_email
from common.const import LDAP_AD_ACCOUNT_DISABLE
from common.utils.http import is_true
from .base import JMSBaseAuthBackend

logger = _LDAPConfig.get_logger()


class LDAPAuthorizationBackend(JMSBaseAuthBackend, LDAPBackend):
    """
    Override this class to override _LDAPUser to LDAPUser
    """
    @staticmethod
    def is_enabled():
        return settings.AUTH_LDAP

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

    def pre_check(self, username, password):
        if not settings.AUTH_LDAP:
            error = 'Not enabled auth ldap'
            return False, error
        if not username:
            error = 'Username is None'
            return False, error
        if not password:
            error = 'Password is None'
            return False, error
        if settings.AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS:
            user_model = self.get_user_model()
            exist = user_model.objects.filter(username=username).exists()
            if not exist:
                error = 'user ({}) is not in the user list'.format(username)
                return False, error
        return True, ''

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


class LDAPUser(_LDAPUser):

    def _search_for_user_dn_from_ldap_util(self):
        from settings.utils import LDAPServerUtil
        util = LDAPServerUtil()
        user_dn = util.search_for_user_dn(self._username)
        return user_dn

    def _search_for_user_dn(self):
        """
        This method was overridden because the AUTH_LDAP_USER_SEARCH
        configuration in the settings.py file
        is configured with a `lambda` problem value
        """

        user_search_union = [
            LDAPSearch(
                USER_SEARCH, ldap.SCOPE_SUBTREE,
                settings.AUTH_LDAP_SEARCH_FILTER
            )
            for USER_SEARCH in str(settings.AUTH_LDAP_SEARCH_OU).split("|")
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
                logger.warning("{} does not have a value for the attribute {}".format(self.dn, attr))
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
