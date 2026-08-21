from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as drf_filters

from perms.const import ActionChoices as PermActionChoices
from orgs.mixins.api import OrgBulkModelViewSet

from .common import ACLUserAssetFilterMixin
from .. import models, serializers

__all__ = ['ClipboardACLViewSet']


class ClipboardACLFilter(ACLUserAssetFilterMixin):
    operations = drf_filters.ChoiceFilter(
        method='filter_operations', label=_("Operations"),
        choices=[
            (choice.name, choice.label)
            for choice in PermActionChoices
            if choice.value & PermActionChoices.clipboard()
        ],
    )

    class Meta:
        model = models.ClipboardACL
        fields = [
            'id', 'name', 'users', 'assets', 'action', 'operations',
        ]

    @staticmethod
    def filter_operations(queryset, name, value):
        operation = PermActionChoices[value].value
        return queryset.filter(
            operations__in=(operation, PermActionChoices.clipboard())
        )


class ClipboardACLViewSet(OrgBulkModelViewSet):
    model = models.ClipboardACL
    filterset_class = ClipboardACLFilter
    search_fields = ['name']
    serializer_class = serializers.ClipboardACLSerializer
