from django.conf import settings
from django.utils.module_loading import import_string

from authentication.const import MFAType


def get_allowed_mfa_types(user=None):
    """User overrides may narrow, but never expand, the system policy."""
    # Preserve legacy behavior for an empty system configuration.
    allowed = set(settings.SECURITY_MFA_METHODS or MFAType.values)
    user_allowed = getattr(user, 'allowed_mfa_types', None)
    if user_allowed:
        allowed.intersection_update(user_allowed)
    return allowed


def get_mfa_method_status():
    """Use the authentication backends as the source of capability status."""
    backends = {
        backend.name: backend
        for backend in map(import_string, settings.MFA_BACKENDS)
    }
    enterprise = bool(settings.XPACK_ENABLED and settings.XPACK_LICENSE_IS_VALID)
    allowed = get_allowed_mfa_types()
    methods = []
    for value, label in MFAType.choices:
        backend = backends.get(value)
        visible = value != MFAType.Face or enterprise
        methods.append({
            'value': value,
            'label': str(label),
            'visible': visible,
            'enabled': bool(visible and backend and backend.global_enabled()),
            'allowed': value in allowed,
        })
    return methods
