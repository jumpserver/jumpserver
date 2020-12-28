from collections import OrderedDict
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.utils import tmp_to_org
from assets.models import SystemUser


class TicketMetaSerializerMixin:
    need_fields_prefix = None

    def get_fields(self):
        fields = super().get_fields()
        if not self.need_fields_prefix:
            return fields
        need_fields = OrderedDict({
            field_name: field for field_name, field in fields.items()
            if field_name.startswith(self.need_fields_prefix)
        })
        return need_fields


class TicketMetaApproveSerializerMixin:

    need_fields_prefix = 'approve_'

    def _filter_approve_resources_by_org(self, model, resources_id):
        with tmp_to_org(self.root.instance.org_id):
            org_resources = model.objects.filter(id__in=resources_id)
        if not org_resources:
            error = _('None of the approved `{}` belong to Organization `{}`'
                      ''.format(model.__name__, self.root.instance.org_name))
            raise serializers.ValidationError(error)
        return org_resources

    @staticmethod
    def _filter_approve_resources_by_queries(model, resources, queries=None):
        if queries:
            resources = resources.filter(**queries)
        if not resources:
            error = _('None of the approved `{}` does not comply with the filtering rules `{}`'
                      ''.format(model.__name__, queries))
            raise serializers.ValidationError(error)
        return resources

    def filter_approve_resources(self, resource_model, resources_id, queries=None):
        resources = self._filter_approve_resources_by_org(resource_model, resources_id)
        resources = self._filter_approve_resources_by_queries(resource_model, resources, queries)
        resources_id = list(resources.values_list('id', flat=True))
        return resources_id

    def filter_approve_system_users(self, system_users_id, queries=None):
        system_users_id = self.filter_approve_resources(
            resource_model=SystemUser, resources_id=system_users_id, queries=queries
        )
        return system_users_id
