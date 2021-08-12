# -*- coding: utf-8 -*-
#
from orgs.models import Organization
from rest_framework import viewsets

from common.permissions import IsValidUser
from common.exceptions import JMSException
from users.models import User
from .. import serializers


class AssigneeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.AssigneeSerializer
    filterset_fields = ('id', 'name', 'username', 'email', 'source')
    search_fields = filterset_fields

    def get_org(self, org_id):
        org = Organization.get_instance(org_id)
        if not org:
            error = ('The organization `{}` does not exist'.format(org_id))
            raise JMSException(error)
        return org

    def get_queryset(self):
        org_id = self.request.query_params.get('org_id')
        type = self.request.query_params.get('type')
        if type == 'super':
            queryset = User.get_super_admins()
        elif type == 'super_admin':
            org = self.get_org(org_id)
            queryset = User.get_super_and_org_admins(org=org)
        else:
            queryset = User.objects.all()
        return queryset
