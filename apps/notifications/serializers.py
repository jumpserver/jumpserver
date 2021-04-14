from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .models import Subscription


class SubscriptionSerializer(BulkOrgResourceModelSerializer):
    receive_backends = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = Subscription
        fields = ('users', 'groups', 'app_name', 'message', 'receive_backends')
