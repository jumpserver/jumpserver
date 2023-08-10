from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.const.choices import Status
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from terminal.const import PublishStatus
from ..models import Applet, AppletPublication, AppletHost

__all__ = [
    'AppletSerializer', 'AppletPublicationSerializer',
]


class AppletPublicationSerializer(serializers.ModelSerializer):
    applet = ObjectRelatedField(attrs=('id', 'name', 'display_name', 'icon', 'version'), label=_("Applet"),
                                queryset=Applet.objects.all())
    host = ObjectRelatedField(queryset=AppletHost.objects.all(), label=_("Host"))
    status = LabeledChoiceField(choices=PublishStatus.choices, label=_("Status"), default=Status.pending)

    class Meta:
        model = AppletPublication
        fields_mini = ['id', 'applet', 'host']
        read_only_fields = ['date_created', 'date_updated']
        fields = fields_mini + ['status', 'comment'] + read_only_fields


class AppletSerializer(serializers.ModelSerializer):
    icon = serializers.ReadOnlyField(label=_("Icon"))
    type = LabeledChoiceField(choices=Applet.Type.choices, label=_("Type"))
    edition = LabeledChoiceField(
        choices=Applet.Edition.choices, label=_("Edition"), required=False,
        default=Applet.Edition.community
    )

    class Meta:
        model = Applet
        fields_mini = ['id', 'name', 'display_name', 'is_active']
        read_only_fields = [
            'icon', 'readme', 'date_created', 'date_updated',
        ]
        fields = fields_mini + [
            'version', 'author', 'type', 'edition',
            'can_concurrent', 'protocols', 'tags', 'comment',
        ] + read_only_fields
