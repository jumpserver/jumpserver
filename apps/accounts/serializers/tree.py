from rest_framework import serializers


__all__ = ['AccountTreeMetricsQuerySerializer']


class AccountTreeResourceSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=('node', 'asset'))
    id = serializers.UUIDField()


class AccountTreeMetricsQuerySerializer(serializers.Serializer):
    resources = AccountTreeResourceSerializer(many=True, allow_empty=False)
    include_descendants = serializers.BooleanField(default=True)

    @staticmethod
    def validate_resources(resources):
        seen = set()
        unique = []
        for resource in resources:
            key = (resource['type'], resource['id'])
            if key not in seen:
                seen.add(key)
                unique.append(resource)
        return unique
