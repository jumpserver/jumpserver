import os
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers import WritableNestedModelSerializer
from common.serializers.fields import ReadableHiddenField
from common.serializers.mixin import CommonBulkModelSerializer
from ops.models import Playbook
from .mixin import ScopeSerializerMixin
from ops.serializers.variable import PlaybookVariableSerializer


def parse_playbook_name(path):
    file_name = os.path.split(path)[-1]
    return file_name.split(".")[-2]


class PlaybookSerializer(ScopeSerializerMixin, CommonBulkModelSerializer, WritableNestedModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    path = serializers.FileField(required=False)
    variable = PlaybookVariableSerializer(many=True, required=False, allow_null=True, label=_('Variable'))
   
    def to_internal_value(self, data):
        name = data.get('name', False)
        if not name and data.get('path'):
            data['name'] = parse_playbook_name(data['path'].name)
        return super().to_internal_value(data)

    class Meta:
        model = Playbook
        read_only_fields = ["id", "date_created", "date_updated", "created_by"]
        fields_m2m = ['variable']
        fields = read_only_fields + fields_m2m + [
            "id", 'path', 'scope', "name", "comment", "creator",
            'create_method', 'vcs_url',
        ]


class PlaybookFileCreateSerializer(serializers.Serializer):
    key = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, write_only=True)
    name = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    is_directory = serializers.BooleanField(required=False, write_only=True)
    content = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, write_only=True)
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    isParent = serializers.BooleanField(read_only=True)
    pId = serializers.CharField(read_only=True)
    open = serializers.BooleanField(read_only=True)
    iconSkin = serializers.CharField(read_only=True)


class PlaybookFileUpdateSerializer(serializers.Serializer):
    key = serializers.CharField(trim_whitespace=False, write_only=True)
    new_name = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, write_only=True)
    is_directory = serializers.BooleanField(required=False, write_only=True)
    content = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False, write_only=True)
