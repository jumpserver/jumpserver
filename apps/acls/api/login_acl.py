from django.db.models.functions import Concat
from django.db.models import F, Value
from rest_framework_bulk.generics import BulkModelViewSet
from common.permissions import IsOrgAdmin
from common.mixins.api import RelationMixin
from ..models import LoginACL
from .. import serializers

__all__ = ['LoginACLViewSet', 'LoginACLUserRelationViewSet']


class LoginACLViewSet(BulkModelViewSet):
    model = LoginACL
    queryset = LoginACL.objects.all()
    filterset_fields = ('name', )
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin, )
    serializer_class = serializers.LoginACLSerializer


class LoginACLUserRelationViewSet(RelationMixin, BulkModelViewSet):
    m2m_field = LoginACL.users.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = [
        'id', 'user', 'loginacl'
    ]
    serializer_class = serializers.LoginACLUserRelationSerializer
    search_fields = [
        'id', 'user__name', 'user__username', 'loginacl__name'
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            user_display=Concat(F('user__name'), Value('('), F('user__username'), Value(')')),
        )
        return queryset
