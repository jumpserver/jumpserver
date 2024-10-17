import os

from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField
from common.serializers.mixin import CommonBulkModelSerializer
from ops.models import Playbook
from .mixin import ScopeSerializerMixin


def parse_playbook_name(path):
    file_name = os.path.split(path)[-1]
    return file_name.split(".")[-2]


class PlaybookSerializer(ScopeSerializerMixin, CommonBulkModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    path = serializers.FileField(required=False)

    def to_internal_value(self, data):
        name = data.get('name', False)
        if not name and data.get('path'):
            data['name'] = parse_playbook_name(data['path'].name)
        return super().to_internal_value(data)

    class Meta:
        model = Playbook
        read_only_fields = ["id", "date_created", "date_updated", "created_by"]
        fields = read_only_fields + [
            "id", 'path', 'scope', "name", "comment", "creator",
            'create_method', 'vcs_url',
        ]
