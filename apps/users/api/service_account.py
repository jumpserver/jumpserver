# -*- coding: utf-8 -*-
#
from rest_framework import viewsets

from common.permissions import WithBootstrapToken
from rbac.models import Role, RoleBinding
from .. import serializers


class ServiceAccountRegistrationViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ServiceAccountSerializer
    permission_classes = (WithBootstrapToken,)
    http_method_names = ['post']

    def perform_create(self, serializer):
        app = serializer.save()
        role = Role.BuiltinRole.system_component.get_role()
        RoleBinding.objects.create(user=app, role=role)
