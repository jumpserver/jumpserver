# -*- coding: utf-8 -*-
#
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from common.serializers.fields import ObjectRelatedField
from common.serializers.mixin import ResourceLabelsMixin
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .. import utils
from ..models import User, UserGroup

__all__ = [
    'UserGroupSerializer',
]


class UserGroupSerializer(ResourceLabelsMixin, BulkOrgResourceModelSerializer):
    users = ObjectRelatedField(
        required=False, many=True, queryset=User.objects,
        attrs=("id", "name", "is_service_account"), label=_('User'),
    )

    class Meta:
        model = UserGroup
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'comment', 'date_created', 'created_by'
        ]
        fields = fields_mini + fields_small + ['users', 'labels']
        extra_kwargs = {
            'created_by': {'label': _('Created by'), 'read_only': True},
            'users_amount': {'label': _('Users amount')},
            'id': {'label': _('ID')},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_fields_queryset()

    def set_fields_queryset(self):
        users_field = self.fields.get('users')
        if users_field:
            users_field.child_relation.queryset = utils.get_current_org_members()

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('users', 'labels', 'labels__label') \
            .annotate(users_amount=Count('users'))
        return queryset
