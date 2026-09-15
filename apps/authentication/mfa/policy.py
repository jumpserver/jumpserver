from django.conf import settings

from authentication.const import MFAType


def get_allowed_mfa_types(user=None):
    user_allowed = getattr(user, 'allowed_mfa_types', None)
    if user_allowed:
        return set(user_allowed)
    return set(settings.SECURITY_MFA_METHODS or MFAType.values)
