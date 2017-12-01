# ~*~ coding: utf-8 ~*~
import base64
from rest_framework import serializers
from audits.models import RecordLog
from audits.backends import record_store


class RecordSerializer(serializers.ModelSerializer):
    """使用这个类作为基础Command Log Serializer类, 用来序列化"""
    class Meta:
        model = RecordLog
        fields = '__all__'

    def create(self, validated_data):
        try:
            output = validated_data['output']
            validated_data['output'] = base64.b64decode(output)
        except IndexError:
            pass
        return record_store.save(**dict(validated_data))
