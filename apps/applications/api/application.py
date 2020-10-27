# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet

from common.exceptions import JMSException
from .. import models
from .. import serializers
from ..hands import IsOrgAdminOrAppUser

__all__ = [
    'ApplicationViewSet',
]


class ApplicationViewSet(OrgBulkModelViewSet):
    model = models.Application
    filter_fields = ('name', 'type', 'category')
    search_fields = filter_fields
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ApplicationSerializer

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        app_type = self.request.query_params.get('type')
        app_category = self.request.query_params.get('category')

        # TODO: app_type invalid
        # TODO: app_category invalid

        attrs_cls = None
        if app_type:
            attrs_cls = models.Category.get_type_serializer_cls(app_type)
        elif self.action in ['list', 'retrieve', 'metadata']:
            if app_category:
                attrs_cls = models.Category.get_category_serializer_cls(app_category)
            else:
                attrs_cls = serializers.CommonCategorySerializer

        if not attrs_cls:
            raise JMSException(detail='Please bring the query parameter Category or Type')

        return type('ApplicationDynamicSerializer', (serializer_class,), {'attrs': attrs_cls()})
