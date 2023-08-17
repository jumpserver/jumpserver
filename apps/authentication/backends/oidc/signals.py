"""
    OpenID Connect relying party (RP) signals
    =========================================

    This modules defines Django signals that can be triggered during the OpenID Connect
    authentication process.

"""

from django.dispatch import Signal

openid_create_or_update_user = Signal()
