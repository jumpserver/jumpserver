"""
    OpenID Connect relying party (RP) signals
    =========================================

    This modules defines Django signals that can be triggered during the OpenID Connect
    authentication process.

"""

from django.dispatch import Signal


openid_create_or_update_user = Signal(
    providing_args=['request', 'user', 'created', 'name', 'username', 'email']
)
openid_user_login_success = Signal(providing_args=['request', 'user'])
openid_user_login_failed = Signal(providing_args=['request', 'username', 'reason'])

