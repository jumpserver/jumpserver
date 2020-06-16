from rest_framework import serializers
from ..hands import SystemUser

__all__ = [
    'SystemUserSerializer',
]


class SystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = [
            'id', 'name', 'username', 'protocol',
            'login_mode', 'login_mode_display',
            'priority', 'username_same_with_user',
            'auto_push', 'cmd_filters', 'sudo', 'shell', 'comment',
            'sftp_root', 'date_created', 'created_by'
        ]
