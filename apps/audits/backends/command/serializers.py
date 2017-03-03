# ~*~ coding: utf-8 ~*~
import base64
from rest_framework import serializers
from audits.models import CommandLog
from audits.backends import command_store


class CommandLogSerializer(serializers.ModelSerializer):
    """使用这个类作为基础Command Log Serializer类, 用来序列化"""

    class Meta:
        model = CommandLog
        fields = '__all__'

    def create(self, validated_data):
        try:
            output = validated_data['output']
            validated_data['output'] = base64.b64decode(output)
        except IndexError:
            pass
        return command_store.save(**dict(validated_data))
