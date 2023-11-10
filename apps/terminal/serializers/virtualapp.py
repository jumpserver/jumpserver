from rest_framework import serializers

from ..models.virtualapp import VirtualApp

__all__ = [
    'VirtualAppSerializer',
]


class VirtualAppSerializer(serializers.ModelSerializer):
    image_protocol = serializers.CharField(max_length=16, default='vnc')
    image_port = serializers.IntegerField(default=5900)

    class Meta:
        model = VirtualApp
        fields_mini = ['id', 'name', 'image_name', 'is_active']
        read_only_fields = [
            'date_created', 'date_updated',
        ]
        fields = fields_mini + [
            'image_protocol', 'image_port', 'protocols', 'comment',
        ] + read_only_fields
