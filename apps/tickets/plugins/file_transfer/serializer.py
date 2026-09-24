from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..resources import AssetAccountRequestSerializer


class RequestSerializer(AssetAccountRequestSerializer):
    direction = serializers.ChoiceField(choices=[('upload', _('Upload')), ('download', _('Download'))], label=_('Direction'))
    paths = serializers.ListField(child=serializers.CharField(max_length=4096), allow_empty=False,
                                 max_length=100, label=_('File paths'))
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=3600, label=_('Validity (seconds)'))
