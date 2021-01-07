# -*- coding: utf-8 -*-
#
from rest_framework import viewsets

from common.permissions import IsValidUser
from common.exceptions import JMSException
from users.models import User
from orgs.utils import get_org_by_id
from .. import serializers


class AssigneeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.AssigneeSerializer
    filterset_fields = ('id', 'name', 'username', 'email', 'source')
    search_fields = filterset_fields

    def get_org(self):
        org_id = self.request.query_params.get('org_id')
        org = get_org_by_id(org_id)
        if not org:
            error = ('The organization `{}` does not exist'.format(org_id))
            raise JMSException(error)
        return org

    def get_queryset(self):
        org = self.get_org()
        queryset = User.get_super_and_org_admins(org=org)
        return queryset
