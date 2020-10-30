from rest_framework import serializers


class NoPasswordSerializer(serializers.JSONField):
    def to_representation(self, value):
        new_value = {}
        for k, v in value.items():
            if 'password' not in k:
                new_value[k] = v
        return new_value

