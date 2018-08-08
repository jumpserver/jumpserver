
from rest_framework.serializers import ModelSerializer
from .models import Organization


class OrgSerializer(ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'date_created']
