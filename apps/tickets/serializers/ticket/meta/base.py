from collections import OrderedDict
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.utils import tmp_to_org
from assets.models import SystemUser


class BaseTicketMetaSerializer(serializers.Serializer):

    class Meta:
        fields = '__all__'

    def get_fields(self):
        fields = super().get_fields()
        required_fields = self.Meta.fields
        if required_fields == '__all__':
            return fields

        fields = OrderedDict({
            field_name: fields.pop(field_name) for field_name in set(required_fields)
            if field_name in fields.keys()
        })
        return fields


class BaseTicketMetaApproveSerializerMixin:

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
