from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import Web
from assets.const.web import WEB_ADVANCED_FIELDS
from assets.validators import normalize_web_origin, validate_web_script
from .common import AssetSerializer

__all__ = ['WebSerializer']


class WebSerializer(AssetSerializer):
    allowed_urls = serializers.ListField(
        child=serializers.CharField(max_length=512, validators=[normalize_web_origin]),
        max_length=100, required=False, label=_("Allowed sites")
    )

    class Meta(AssetSerializer.Meta):
        model = Web
        fields = AssetSerializer.Meta.fields + [
            'autofill', 'username_selector',
            'password_selector', 'submit_selector',
            'success_selector', 'interactive_selector', 'script', 'allowed_urls'
        ]
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'address': {
                'label': 'URL'
            },
            'username_selector': {
                'default': 'name=username'
            },
            'password_selector': {
                'default': 'name=password'
            },
            'submit_selector': {
                'default': 'id=login_button',
            },
            'success_selector': {
                'required': False,
                'allow_blank': True,
                'default': '',
            },
            'interactive_selector': {
                'required': False,
                'allow_blank': True,
                'default': '',
            },
            'script': {
                'default': [],
            }
        }

    def get_fields(self):
        fields = super().get_fields()
        if not settings.XPACK_LICENSE_IS_VALID:
            fields['autofill'].choices = [
                (key, label) for key, label in fields['autofill'].choices.items() if key != 'script'
            ]
            for name in WEB_ADVANCED_FIELDS:
                fields[name].read_only = True
        return fields

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not settings.XPACK_LICENSE_IS_VALID:
            return attrs
        interactive = attrs.get('interactive_selector', getattr(self.instance, 'interactive_selector', ''))
        if interactive:
            kind, separator, value = interactive.partition('=')
            if not separator or not value.strip() or kind.strip().lower() not in (
                'name', 'id', 'type', 'class_name', 'css', 'css_selector', 'xpath'
            ):
                raise serializers.ValidationError({'interactive_selector': _('Invalid selector')})
        return attrs

    def validate_script(self, value):
        autofill = getattr(self, 'initial_data', {}).get(
            'autofill', getattr(self.instance, 'autofill', 'basic')
        )
        if autofill == 'script':
            validate_web_script(value)
        return value

    def to_internal_value(self, data):
        data = data.copy()
        if data.get('script') in ("", None):
            data.pop('script', None)
        return super().to_internal_value(data)
