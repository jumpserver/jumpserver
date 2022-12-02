import os

from rest_framework import serializers

from common.drf.fields import ReadableHiddenField
from ops.models import Playbook


def parse_playbook_name(path):
    file_name = os.path.split(path)[-1]
    return file_name.split(".")[-2]


class PlaybookSerializer(serializers.ModelSerializer):
    owner = ReadableHiddenField(default=serializers.CurrentUserDefault())

    def create(self, validated_data):
        name = validated_data.get('name')
        if not name:
            path = validated_data.get('path').name
            validated_data['name'] = parse_playbook_name(path)
        return super().create(validated_data)

    class Meta:
        model = Playbook
        fields = [
            "id", "name", "path", "date_created", "owner", "date_updated"
        ]
