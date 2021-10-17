from rest_framework import viewsets

from common.permissions import IsOrgAdmin
from common.mixins.api import CommonApiMixin
from ..models import LoginACL
from .. import serializers
from ..filters import LoginAclFilter

__all__ = ['LoginACLViewSet', ]


class LoginACLViewSet(CommonApiMixin, viewsets.ModelViewSet):
    queryset = LoginACL.objects.all()
    filterset_class = LoginAclFilter
    search_fields = ('name',)
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.LoginACLSerializer
