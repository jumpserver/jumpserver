from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.const import FillType
from assets.models import Database, Web
from common.serializers.fields import LabeledChoiceField


class DatabaseSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = Database
        fields = ['db_name', 'use_ssl', 'allow_invalid_cert']


class WebSpecSerializer(serializers.ModelSerializer):
    autofill = LabeledChoiceField(choices=FillType.choices, label=_('Autofill'))

    class Meta:
        model = Web
        fields = [
            'autofill', 'username_selector', 'password_selector',
            'submit_selector', 'script'
        ]


category_spec_serializer_map = {
    'database': DatabaseSpecSerializer,
    'web': WebSpecSerializer,
}
