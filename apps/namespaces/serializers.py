from rest_framework import serializers

from namespaces.models import Namespace


class NamespaceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Namespace
        fields = ('id', 'name', 'comment', 'created_by', 'updated_by', 'date_created', 'date_updated')
        read_only_fields = ('id', 'created_by', 'updated_by',)
