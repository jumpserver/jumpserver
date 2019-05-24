# coding:utf-8
#

import ldap
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django_auth_ldap.backend import _LDAPUser, LDAPBackend
from django_auth_ldap.config import _LDAPConfig, LDAPSearch, LDAPSearchUnion

from users.utils import construct_user_email

logger = _LDAPConfig.get_logger()


class LDAPAuthorizationBackend(LDAPBackend):
    """
    Override this class to override _LDAPUser to LDAPUser
    """

    def authenticate(self, request=None, username=None, password=None, **kwargs):
        logger.info('Authentication LDAP backend')
        if not username:
            logger.info('Authenticate failed: username is None')
            return None
        ldap_user = LDAPUser(self, username=username.strip(), request=request)
        user = self.authenticate_ldap_user(ldap_user, password)
        logger.info('Authenticate user: {}'.format(user))
        return user

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
            user_dn = None

        return user_dn

    def _populate_user_from_attributes(self):
        for field, attr in self.settings.USER_ATTR_MAP.items():
            try:
                value = self.attrs[attr][0]
            except LookupError:
                logger.warning("{} does not have a value for the attribute {}".format(self.dn, attr))
            else:
                if not hasattr(self._user, field):
                    continue
                if isinstance(getattr(self._user, field), bool):
                    value = value.lower() in ['true', '1']
                setattr(self._user, field, value)

        email = getattr(self._user, 'email', '')
        email = construct_user_email(email, self._user.username)
        setattr(self._user, 'email', email)
