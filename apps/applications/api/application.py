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
        type_options = list(dict(models.Category.get_all_type_serializer_mapper()).keys())
        category_options = list(dict(models.Category.get_category_serializer_mapper()).keys())

        if app_type and app_type not in type_options:
            raise JMSException(
                'Invalid query parameter `type`, select from the following options: {}'
                ''.format(type_options)
            )
        if app_category and app_category not in category_options:
            raise JMSException(
                'Invalid query parameter `category`, select from the following options: {}'
                ''.format(category_options)
            )

        if self.action in [
            'create', 'update', 'partial_update', 'bulk_update', 'partial_bulk_update'
        ] and not app_type:
            # action: create / update ...
            raise JMSException(
                'The `{}` action must take the `type` query parameter'.format(self.action)
            )

        if app_type:
            attrs_cls = models.Category.get_type_serializer_cls(app_type)
        elif app_category:
            # action: list / retrieve / metadata
            attrs_cls = models.Category.get_category_serializer_cls(app_category)
        else:
            attrs_cls = serializers.CommonCategorySerializer
        return type('ApplicationDynamicSerializer', (serializer_class,), {'attrs': attrs_cls()})
