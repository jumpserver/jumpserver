from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.const import Language


class LanguageChoiceField(serializers.ChoiceField):
    @staticmethod
    def normalize(value):
        if not isinstance(value, str):
            return value
        return Language.get_code_mapper().get(value.lower(), value)

    def to_internal_value(self, data):
        return super().to_internal_value(self.normalize(data))

    def to_representation(self, value):
        return super().to_representation(self.normalize(value))


class BasicSerializer(serializers.Serializer):
    lang = LanguageChoiceField(
        required=False,
        choices=Language.choices_supported(),
        label=_('Language'),
        default=Language.en,
    )


class LinaSerializer(serializers.Serializer):
    basic = BasicSerializer(required=False, label=_('Basic'))
