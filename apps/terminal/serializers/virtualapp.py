from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.const.choices import Status
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from terminal.const import PublishStatus
from ..models import VirtualApp, VirtualAppPublication, VirtualHost

__all__ = [
    'VirtualAppSerializer', 'VirtualAppPublicationSerializer'
]


class VirtualAppSerializer(serializers.ModelSerializer):
    image_protocol = serializers.CharField(max_length=16, default='vnc')
    image_port = serializers.IntegerField(default=5900)

    class Meta:
        model = VirtualApp
        fields_mini = ['id', 'name', 'image_name', 'is_active']
        read_only_fields = [
            'date_created', 'date_updated',
        ]
        fields = fields_mini + [
            'image_protocol', 'image_port', 'protocols', 'comment',
        ] + read_only_fields


class VirtualAppPublicationSerializer(serializers.ModelSerializer):
    app = ObjectRelatedField(attrs=('id', 'name', 'image_name',), label=_("Virtual App"),
                             queryset=VirtualApp.objects.all())
    vhost = ObjectRelatedField(queryset=VirtualHost.objects.all(), label=_("Virtual Host"))
    status = LabeledChoiceField(choices=PublishStatus.choices, label=_("Status"), default=Status.pending)

    class Meta:
        model = VirtualAppPublication
        fields_mini = ['id', 'vhost', 'app']
        read_only_fields = ['date_created', 'date_updated']
        fields = fields_mini + ['status', 'comment'] + read_only_fields
