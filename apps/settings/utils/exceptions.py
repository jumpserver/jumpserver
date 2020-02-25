from ldap3.core.exceptions import LDAPExceptionError


class LDAPInvalidSearchOuOrFilterError(LDAPExceptionError):
    pass


class LDAPNotEnabledAuthError(LDAPExceptionError):
    pass
