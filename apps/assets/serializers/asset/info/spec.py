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

    def get_fields(self):
        fields = super().get_fields()
        if self.is_retrieve():
            # 查看 Web 资产详情时
            self.pop_fields_if_need(fields)
        return fields
    
    def is_retrieve(self):
        try:
            self.context.get('request').method and self.parent.instance.web
            return True
        except Exception:
            return False

    def pop_fields_if_need(self, fields):
        fields_script = ['script']
        fields_basic = ['username_selector', 'password_selector', 'submit_selector']
        autofill = self.parent.instance.web.autofill
        pop_fields_mapper = {
            FillType.no: fields_script + fields_basic,
            FillType.basic: fields_script,
            FillType.script: fields_basic,
        }
        fields_pop = pop_fields_mapper.get(autofill, [])
        for f in fields_pop:
            fields.pop(f, None)
        return fields




category_spec_serializer_map = {
    'database': DatabaseSpecSerializer,
    'web': WebSpecSerializer,
}
