from django.conf import settings

from authentication.const import MFAType


def get_allowed_mfa_types(user=None):
    allowed = set(settings.SECURITY_MFA_METHODS or MFAType.values)
    if user is not None and getattr(user, 'allowed_mfa_types', None):
        allowed &= set(user.allowed_mfa_types)
    return allowed
