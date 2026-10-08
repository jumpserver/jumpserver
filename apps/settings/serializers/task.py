from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = ['TaskNoticeSettingSerializer']


class TaskNoticeSettingSerializer(serializers.Serializer):
    USER_EXPIRED_FIRST_NOTICE_DAYS = serializers.IntegerField(
        min_value=1, max_value=3650, label=_('First notice'),
    )
    USER_EXPIRED_DAILY_NOTICE_DAYS = serializers.IntegerField(
        min_value=1, max_value=365, label=_('Daily notice'),
    )
    PERM_EXPIRED_FIRST_NOTICE_DAYS = serializers.IntegerField(
        min_value=1, max_value=3650, label=_('First notice'),
    )
    PERM_EXPIRED_DAILY_NOTICE_DAYS = serializers.IntegerField(
        min_value=1, max_value=365, label=_('Daily notice'),
    )

    notice_field_pairs = (
        ('USER_EXPIRED_FIRST_NOTICE_DAYS', 'USER_EXPIRED_DAILY_NOTICE_DAYS'),
        ('PERM_EXPIRED_FIRST_NOTICE_DAYS', 'PERM_EXPIRED_DAILY_NOTICE_DAYS'),
    )

    def validate(self, attrs):
        for first_name, daily_name in self.notice_field_pairs:
            if first_name not in attrs and daily_name not in attrs:
                continue
            first_days = attrs.get(first_name, getattr(settings, first_name))
            daily_days = attrs.get(daily_name, getattr(settings, daily_name))
            if first_days < daily_days:
                message = _('First notice days must be greater than or equal to daily notice days.')
                raise serializers.ValidationError({first_name: message})
        return attrs
