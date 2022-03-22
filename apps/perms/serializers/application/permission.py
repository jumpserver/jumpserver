# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from perms.models import ApplicationPermission, Action
from ..base import ActionsField, BasePermissionSerializer

__all__ = [
    'ApplicationPermissionSerializer'
]


class ApplicationPermissionSerializer(BasePermissionSerializer):
    actions = ActionsField(required=False, allow_null=True, label=_("Actions"))
    category_display = serializers.ReadOnlyField(source='get_category_display', label=_('Category display'))
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type display'))
    is_valid = serializers.BooleanField(read_only=True, label=_('Is valid'))
    is_expired = serializers.BooleanField(read_only=True, label=_("Is expired"))

    class Meta:
        model = ApplicationPermission
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'category', 'category_display', 'type', 'type_display',
            'actions',
            'is_active', 'is_expired', 'is_valid',
            'created_by', 'date_created', 'date_expired', 'date_start', 'comment', 'from_ticket'
        ]
        fields_m2m = [
            'users', 'user_groups', 'applications', 'system_users',
            'users_amount', 'user_groups_amount', 'applications_amount',
            'system_users_amount',
        ]
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created', 'from_ticket']
        extra_kwargs = {
            'is_expired': {'label': _('Is expired')},
            'is_valid': {'label': _('Is valid')},
            'actions': {'label': _('Actions')},
            'users_amount': {'label': _('Users amount')},
            'user_groups_amount': {'label': _('User groups amount')},
            'system_users_amount': {'label': _('System users amount')},
            'applications_amount': {'label': _('Apps amount')},
        }

    def _filter_actions_choices(self, choices):
        if request := self.context.get('request'):
            category = request.query_params.get('category')
        else:
            category = None
        exclude_choices = ApplicationPermission.get_exclude_actions_choices(category=category)
        for choice in exclude_choices:
            choices.pop(choice, None)
        return choices

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related(
            'users', 'user_groups', 'applications', 'system_users'
        )
        return queryset

    def validate_applications(self, applications):
        if self.instance:
            permission_type = self.instance.type
        else:
            permission_type = self.initial_data['type']

        other_type_applications = [
            application for application in applications
            if application.type != permission_type
        ]
        if len(other_type_applications) > 0:
            error = _(
                'The application list contains applications '
                'that are different from the permission type. ({})'
            ).format(', '.join([application.name for application in other_type_applications]))
            raise serializers.ValidationError(error)
        return applications
