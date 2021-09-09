from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class BasicSettingSerializer(serializers.Serializer):
    SITE_URL = serializers.URLField(
        required=True, label=_("Site url"),
        help_text=_('eg: http://dev.jumpserver.org:8080')
    )
    USER_GUIDE_URL = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, label=_("User guide url"),
        help_text=_('User first login update profile done redirect to it')
    )
    FORGOT_PASSWORD_URL = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, label=_("Forgot password url"),
        help_text=_('The forgot password url on login page, If you use '
                    'ldap or cas external authentication, you can set it')
    )
    GLOBAL_ORG_DISPLAY_NAME = serializers.CharField(
        required=False, max_length=1024, allow_blank=True, allow_null=True, label=_("Global organization name"),
        help_text=_('The name of global organization to display')
    )
