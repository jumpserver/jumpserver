from django.utils.translation import ugettext_lazy as _
from rest_framework.authtoken.models import Token


class PrivateToken(Token):
    """Inherit from auth token, otherwise migration is boring"""

    class Meta:
        verbose_name = _('Private Token')
