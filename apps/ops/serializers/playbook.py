import os

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField, LabeledChoiceField
from common.serializers.mixin import CommonBulkModelSerializer
from ops.models import Playbook
from ..const import Scope


def parse_playbook_name(path):
    file_name = os.path.split(path)[-1]
    return file_name.split(".")[-2]


class PlaybookSerializer(CommonBulkModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    path = serializers.FileField(required=False)
    scope = LabeledChoiceField(
        choices=Scope.choices, default=Scope.public, label=_("Scope")
    )
    disable_edit = serializers.SerializerMethodField()

    def to_internal_value(self, data):
        name = data.get('name', False)
        if not name and data.get('path'):
            data['name'] = parse_playbook_name(data['path'].name)
        return super().to_internal_value(data)

    def get_disable_edit(self, obj):
        return obj.creator != self.context['request'].user

    class Meta:
        model = Playbook
        read_only_fields = ["id", "date_created", "date_updated", "disable_edit"]
        fields = read_only_fields + [
            "id", 'path', 'scope', 'participants', "name", "comment", "creator",
            'create_method', 'vcs_url',
        ]
