import os

from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField
from ops.models import Playbook
from orgs.mixins.serializers import BulkOrgResourceModelSerializer


def parse_playbook_name(path):
    file_name = os.path.split(path)[-1]
    return file_name.split(".")[-2]


class PlaybookSerializer(BulkOrgResourceModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    path = serializers.FileField(required=False)

    def to_internal_value(self, data):
        name = data.get('name', False)
        if not name and data.get('path'):
            data['name'] = parse_playbook_name(data['path'].name)
        return super().to_internal_value(data)

    class Meta:
        model = Playbook
        read_only_fields = ["id", "date_created", "date_updated"]
        fields = read_only_fields + [
            "id", 'path', "name", "comment", "creator",
            'create_method', 'vcs_url',
        ]
