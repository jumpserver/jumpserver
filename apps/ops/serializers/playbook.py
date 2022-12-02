import os

from rest_framework import serializers

from common.drf.fields import ReadableHiddenField
from ops.models import Playbook
from orgs.mixins.serializers import BulkOrgResourceModelSerializer


def parse_playbook_name(path):
    file_name = os.path.split(path)[-1]
    return file_name.split(".")[-2]


class PlaybookSerializer(BulkOrgResourceModelSerializer, serializers.ModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    path = serializers.FileField(required=False)

    def create(self, validated_data):
        name = validated_data.get('name')
        if not name:
            path = validated_data.get('path').name
            validated_data['name'] = parse_playbook_name(path)
        return super().create(validated_data)

    class Meta:
        model = Playbook
        read_only_fields = ["id", "date_created", "date_updated"]
        fields = read_only_fields + [
            "id", 'path', "name", "comment", "creator",
        ]
