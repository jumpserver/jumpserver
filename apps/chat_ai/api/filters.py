from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as drf_filters

from common.drf.filters import BaseFilterSet

from chat_ai.models import Conversation


class ConversationAuditFilterSet(BaseFilterSet):
    title = drf_filters.CharFilter(
        lookup_expr='icontains', label=_('Title')
    )
    user__username = drf_filters.CharFilter(
        field_name='user__username', lookup_expr='icontains',
        label=_('Username'),
    )

    class Meta:
        model = Conversation
        fields = ('title', 'user__username')
