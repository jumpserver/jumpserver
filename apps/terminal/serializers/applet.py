from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db import models

from common.drf.fields import ObjectRelatedField, LabeledChoiceField
from ..models import Applet, AppletPublication, AppletHost


__all__ = [
    'AppletSerializer', 'AppletPublicationSerializer',
]


class AppletPublicationSerializer(serializers.ModelSerializer):
    class Status(models.TextChoices):
        PUBLISHED = 'published', _('Published')
        UNPUBLISHED = 'unpublished', _('Unpublished')
        NOT_MATCH = 'not_match', _('Not match')

    applet = ObjectRelatedField(attrs=('id', 'name', 'display_name', 'icon', 'version'), queryset=Applet.objects.all())
    host = ObjectRelatedField(queryset=AppletHost.objects.all())
    status = LabeledChoiceField(choices=Status.choices, label=_("Status"))

    class Meta:
        model = AppletPublication
        fields_mini = ['id', 'applet', 'host']
        read_only_fields = ['date_created', 'date_updated']
        fields = fields_mini + ['status', 'comment'] + read_only_fields


class AppletSerializer(serializers.ModelSerializer):
    icon = serializers.ReadOnlyField(label=_("Icon"))
    type = LabeledChoiceField(choices=Applet.Type.choices, label=_("Type"))

    class Meta:
        model = Applet
        fields_mini = ['id', 'name', 'display_name']
        read_only_fields = [
            'icon', 'date_created', 'date_updated',
        ]
        fields = fields_mini + [
            'version', 'author', 'type', 'protocols',
            'tags', 'comment'
        ] + read_only_fields
