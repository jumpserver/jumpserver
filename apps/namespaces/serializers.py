from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from namespaces.models import Namespace


class NamespaceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Namespace
        fields = ('id', 'name', 'comment', 'created_by', 'updated_by', 'date_created', 'date_updated')
        read_only_fields = ('id', 'created_by', 'updated_by',)

    def validate(self, attrs):
        org_id = attrs.get('org_id', '')
        name = attrs.get('name')
        queryset = Namespace.objects.filter(org_id=org_id, name=name)
        if queryset:
            raise serializers.ValidationError({'name': _('Duplicate name')})
        return attrs
