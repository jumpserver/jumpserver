from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.const.choices import Status
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from terminal.const import PublishStatus
from ..models import VirtualApp, VirtualAppPublication, AppProvider

__all__ = [
    'VirtualAppSerializer', 'VirtualAppPublicationSerializer'
]


class VirtualAppSerializer(serializers.ModelSerializer):
    icon = serializers.ReadOnlyField(label=_("Icon"))
    image_protocol = serializers.CharField(max_length=16, default='vnc')
    image_port = serializers.IntegerField(default=5900)

    class Meta:
        model = VirtualApp
        fields_mini = ['id', 'display_name', 'name', 'image_name', 'is_active']
        read_only_fields = [
            'icon', 'readme', 'date_created', 'date_updated',
        ]
        fields = fields_mini + [
            'version', 'author', 'image_protocol', 'image_port',
            'protocols', 'tags', 'comment',
        ] + read_only_fields


class VirtualAppPublicationSerializer(serializers.ModelSerializer):
    app = ObjectRelatedField(attrs=('id', 'name', 'image_name',), label=_("Virtual app"),
                             queryset=VirtualApp.objects.all())
    provider = ObjectRelatedField(queryset=AppProvider.objects.all(), label=_("App Provider"))
    status = LabeledChoiceField(choices=PublishStatus.choices, label=_("Status"), default=Status.pending)

    class Meta:
        model = VirtualAppPublication
        fields_mini = ['id', 'provider', 'app']
        read_only_fields = ['date_created', 'date_updated']
        fields = fields_mini + ['status', 'comment'] + read_only_fields
