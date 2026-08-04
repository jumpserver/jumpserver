from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from orgs.utils import filter_org_queryset
from terminal.const import RiskLevelChoices
from terminal.models import Command, CommandStorage, Session


class CommandFilter(BaseFilterSet):
    id = filters.UUIDFilter(
        method='filter_exact', label=_('Command ID')
    )
    date_from = filters.DateTimeFilter(
        method='do_nothing', label=_('Date from')
    )
    date_to = filters.DateTimeFilter(method='do_nothing', label=_('Date to'))
    session_id = filters.CharFilter(
        field_name='session', label=_('Session ID')
    )
    command_storage_id = filters.UUIDFilter(
        method='do_nothing', label=_('Command storage ID')
    )
    user = filters.CharFilter(
        method='filter_startswith', label=_('User name')
    )
    input = filters.CharFilter(
        method='filter_icontains', label=_('Command')
    )
    asset = filters.CharFilter(
        method='filter_icontains', label=_('Asset name')
    )
    asset_id = filters.UUIDFilter(
        method='filter_by_asset_id', label=_('Asset ID')
    )
    account = filters.CharFilter(
        method='filter_exact', label=_('Account name')
    )
    session = filters.CharFilter(
        method='filter_exact', label=_('Session ID')
    )
    risk_level = filters.ChoiceFilter(
        method='filter_exact', choices=RiskLevelChoices.choices,
        label=_('Risk level')
    )

    class Meta:
        model = Command
        fields = [
            'id', 'user', 'asset', 'asset_id', 'account', 'input',
            'risk_level', 'session',
        ]
        fields_operator = {
            'id': ('exact',),
            'user': ('startswith',),
            'asset': ('icontains',),
            'asset_id': ('exact',),
            'account': ('exact',),
            'input': ('icontains',),
            'session': ('exact',),
        }

    @staticmethod
    def filter_exact(queryset, name, value):
        return queryset.filter(**{name: value})

    @staticmethod
    def filter_startswith(queryset, name, value):
        return queryset.filter(**{f'{name}__startswith': value})

    @staticmethod
    def filter_icontains(queryset, name, value):
        return queryset.filter(**{f'{name}__icontains': value})

    def do_nothing(self, queryset, name, value):
        return queryset

    @property
    def qs(self):
        qs = super().qs
        qs = filter_org_queryset(qs)
        qs = self.filter_by_timestamp(qs)
        return qs

    def filter_by_timestamp(self, qs: QuerySet):
        date_from = self.form.cleaned_data.get('date_from')
        date_to = self.form.cleaned_data.get('date_to')

        _filters = {}
        if date_from:
            date_from = date_from.timestamp()
            _filters['timestamp__gte'] = date_from

        if date_to:
            date_to = date_to.timestamp()
            _filters['timestamp__lte'] = date_to

        qs = qs.filter(**_filters)
        return qs

    def filter_by_asset_id(self, queryset, name, value):
        asset_id = self.form.cleaned_data.get('asset_id')
        filters = {}
        if asset_id:
            session_ids = Session.objects.filter(asset_id=asset_id).values_list('id', flat=True)
            filters['session__in'] = list(session_ids)
        queryset = queryset.filter(**filters)
        return queryset


class CommandFilterForStorageTree(CommandFilter):
    asset = filters.CharFilter(method='do_nothing', label=_('Asset'))
    account = filters.CharFilter(method='do_nothing', label=_('Account'))
    session = filters.CharFilter(method='do_nothing', label=_('Session'))
    risk_level = filters.NumberFilter(
        method='do_nothing', label=_('Risk level')
    )

    class Meta:
        model = CommandStorage
        fields = [
            'asset', 'account', 'user', 'session', 'risk_level', 'input',
            'date_from', 'date_to', 'session_id', 'risk_level', 'command_storage_id',
        ]


class CommandStorageFilter(filters.FilterSet):
    real = filters.BooleanFilter(
        method='filter_real', label=_('Real storage')
    )

    class Meta:
        model = CommandStorage
        fields = ['real', 'name', 'type', 'is_default']

    def filter_real(self, queryset, name, value):
        if value:
            queryset = queryset.exclude(name='null')
        return queryset
