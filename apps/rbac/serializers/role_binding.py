from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from ..models import SafeRoleBinding


__all__ = ['SafeRoleBindingSerializer']


class SafeRoleBindingSerializer(serializers.ModelSerializer):

    class Meta:
        model = SafeRoleBinding
        fields = ['id', 'user', 'role', 'safe']
