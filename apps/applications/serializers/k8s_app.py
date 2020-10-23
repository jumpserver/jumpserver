from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .. import models


class CloudCategorySerializer(serializers.Serializer):
    cluster = serializers.CharField(label=_('Cluster'))


class K8sAttrsSerializer(CloudCategorySerializer):
    pass


class K8sAppSerializer(BulkOrgResourceModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = models.K8sApp
        fields = [
            'id', 'name', 'type', 'type_display', 'comment', 'created_by',
            'date_created', 'date_updated', 'cluster'
        ]
        read_only_fields = [
            'id', 'created_by', 'date_created', 'date_updated',
        ]
