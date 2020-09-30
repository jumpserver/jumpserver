from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


__all__ = ['ContentTypeSerializer', 'PermissionSerializer']


class ContentTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContentType
        fields = (
            'id', 'app_label', 'model'
        )
        read_only_fields = ('id',)


class PermissionSerializer(serializers.ModelSerializer):
    content_type_display = serializers.SerializerMethodField(help_text=_('app_label-model'))

    class Meta:
        model = Permission
        fields = (
            'id', 'name', 'content_type', 'content_type_display', 'codename',
        )
        read_only_fields = ('id',)

    @staticmethod
    def get_content_type_display(obj):
        return obj.content_type.app_label + '-' + obj.content_type.model
