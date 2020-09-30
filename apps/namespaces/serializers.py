from rest_framework import serializers

from namespaces.models import Namespace


class NamespaceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Namespace
        fields = ('id', 'name', 'comment')
        read_only_fields = ('id',)
