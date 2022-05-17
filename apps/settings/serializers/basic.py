import uuid

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


class AnnouncementSerializer(serializers.Serializer):
    ID = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    SUBJECT = serializers.CharField(required=True, max_length=1024, label=_("Subject"))
    CONTENT = serializers.CharField(label=_("Content"))
    LINK = serializers.URLField(
        required=False, allow_null=True, allow_blank=True,
        label=_("More url"), default='',
    )

    def to_representation(self, instance):
        defaults = {'ID': '', 'SUBJECT': '', 'CONTENT': '', 'LINK': '', 'ENABLED': False}
        data = {**defaults, **instance}
        return super().to_representation(data)

    def to_internal_value(self, data):
        data['ID'] = str(uuid.uuid4())
        return super().to_internal_value(data)


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
    ANNOUNCEMENT_ENABLED = serializers.BooleanField(label=_('Enable announcement'), default=True)
    ANNOUNCEMENT = AnnouncementSerializer(label=_("Announcement"))
    TICKETS_ENABLED = serializers.BooleanField(required=False, default=True, label=_("Enable tickets"))

    @staticmethod
    def validate_SITE_URL(s):
        if not s:
            return 'http://127.0.0.1'
        return s.strip('/')

