from rest_framework import serializers
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from assets.models import Platform
from assets.serializers.asset import ProtocolsField
from assets.const import Protocol
from .mixin import CategoryDisplayMixin

__all__ = ['PlatformSerializer']


class PlatformSerializer(CategoryDisplayMixin, serializers.ModelSerializer):
    meta = serializers.DictField(required=False, allow_null=True, label=_('Meta'))
    protocols_default = ProtocolsField(label=_('Protocols'), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO 修复 drf SlugField RegexValidator bug，之后记得删除
        validators = self.fields['name'].validators
        if isinstance(validators[-1], RegexValidator):
            validators.pop()
        self.set_platform_meta()

    def set_platform_meta(self):
        view = self.context.get('view')
        if not view:
            return
        request = view.request

        if isinstance(self.instance, Platform):
            category = self.instance.category
            tp = self.instance.type
        else:
            tp = request.query_params.get('type')
            category = request.query_params.get('category')

        print("Request: {}".format(self.context.get('request').method), category, tp)
        if not all([tp, category]):
            return
        meta = Platform.get_type_meta(category, tp)
        print("Platform meta: {}".format(meta))
        protocols_default = self.fields['protocols_default']
        limits = meta.get('protocols_limit', [])
        default_ports = Protocol.default_ports()
        protocols = []
        for protocol in limits:
            port = default_ports.get(protocol, 22)
            protocols.append(f'{protocol}/{port}')
        print("set ptocols: ", protocols)
        protocols_default.set_protocols(protocols)

    class Meta:
        model = Platform
        fields_mini = ['id', 'name', 'internal']
        fields_small = fields_mini + [
            'meta', 'comment', 'charset',
            'category', 'category_display',
            'type', 'type_display',
        ]
        fields_fk = [
            'domain_enabled', 'domain_default',
            'protocols_enabled', 'protocols_default',
            'admin_user_enabled', 'admin_user_default',
        ]
        fields = fields_small + fields_fk
        read_only_fields = [
            'category_display', 'type_display',
        ]


