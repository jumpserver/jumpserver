from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from common.utils import is_uuid
from .models import AuditConversation


class ConversationAuditFilterSet(BaseFilterSet):
    title = filters.CharFilter(lookup_expr='iexact', label=_('Title'))
    user = filters.CharFilter(method='filter_user', label=_('User'))

    @staticmethod
    def filter_user(queryset, name, value):
        query = Q(subject_name__icontains=value) | Q(subject_username__icontains=value)
        if is_uuid(value):
            query |= Q(subject_id=value)
        return queryset.filter(query)

    class Meta:
        model = AuditConversation
        fields = ('id', 'title', 'user')
        fields_operator = {'user': ('icontains',)}
