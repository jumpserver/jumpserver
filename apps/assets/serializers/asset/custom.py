from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import Custom, Platform
from common.serializers import MethodSerializer
from common.serializers.dynamic import create_serializer_class
from .common import AssetSerializer

__all__ = ['CustomSerializer']


class CustomSerializer(AssetSerializer):
    info = MethodSerializer(label=_('Info'))

    class Meta(AssetSerializer.Meta):
        model = Custom
        fields = AssetSerializer.Meta.fields + ['info']

    def get_info_serializer(self):
        request = self.context.get('request')

        if not request or not request.query_params.get('platform'):
            # user_agent = request.META.get('HTTP_USER_AGENT')
            return serializers.DictField()
            # if request.method.lower() != 'post' or not user_agent or 'swagger' in user_agent:
            # else:
            #     raise serializers.ValidationError('platform is required')

        platform_id = request.query_params.get('platform')
        platform = get_object_or_404(Platform, id=platform_id)
        custom_fields = platform.custom_fields
        if not custom_fields:
            return serializers.DictField()
        name = platform.name.title() + 'CustomSerializer'
        return create_serializer_class(name, custom_fields)()
