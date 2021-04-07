from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from ..models import SafeRoleBinding


__all__ = ['SafeRoleBindingSerializer']


class SafeRoleBindingSerializer(serializers.ModelSerializer):
    role_permissions = serializers.ListField(
        source='role.get_permissions_display', read_only=True, label=_('Role permissions display')
    )
    user_display = serializers.CharField(
        source='user.name', read_only=True, label=_('User display')
    )
    safe_display = serializers.CharField(
        source='safe.name', read_only=True, label=_('Safe display')
    )

    class Meta:
        model = SafeRoleBinding
        fields = ['id', 'user', 'user_display', 'role', 'role_permissions', 'safe', 'safe_display']
