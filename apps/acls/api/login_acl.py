from rest_framework_bulk.generics import BulkModelViewSet
from common.permissions import IsOrgAdmin
from ..models import LoginACL
from .. import serializers

__all__ = ['LoginACLViewSet']


class LoginACLViewSet(BulkModelViewSet):
    model = LoginACL
    queryset = LoginACL.objects.all()
    filterset_fields = ('name', )
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin, )
    serializer_class = serializers.LoginACLSerializer
