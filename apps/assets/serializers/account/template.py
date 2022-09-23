from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.models import AccountTemplate
from .base import BaseAccountSerializer


class AccountTemplateSerializer(BaseAccountSerializer):
    class Meta(BaseAccountSerializer.Meta):
        model = AccountTemplate

    @classmethod
    def validate_required(cls, attrs):
        # Todo: why ?
        required_field_dict = {}
        error = _('This field is required.')
        for k, v in cls().fields.items():
            if v.required and k not in attrs:
                required_field_dict[k] = error
        if not required_field_dict:
            return
        raise serializers.ValidationError(required_field_dict)

