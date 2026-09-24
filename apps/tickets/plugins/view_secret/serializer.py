from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..resources import AssetAccountRequestSerializer


class RequestSerializer(AssetAccountRequestSerializer):
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=600, label=_('Validity (seconds)'))
