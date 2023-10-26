from django.db.models import QuerySet
from django_filters import rest_framework as filters

from orgs.utils import filter_org_queryset
from terminal.models import Command, CommandStorage


class CommandFilter(filters.FilterSet):
    date_from = filters.DateTimeFilter(method='do_nothing')
    date_to = filters.DateTimeFilter(method='do_nothing')
    session_id = filters.CharFilter(field_name='session')
    command_storage_id = filters.UUIDFilter(method='do_nothing')
    user = filters.CharFilter(lookup_expr='startswith')
    input = filters.CharFilter(lookup_expr='icontains')
    asset = filters.CharFilter(field_name='asset', lookup_expr='icontains')

    class Meta:
        model = Command
        fields = [
            'asset', 'account', 'user', 'session', 'risk_level', 'input',
            'date_from', 'date_to', 'session_id', 'risk_level', 'command_storage_id',
        ]

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

        filters = {}
        if date_from:
            date_from = date_from.timestamp()
            filters['timestamp__gte'] = date_from

        if date_to:
            date_to = date_to.timestamp()
            filters['timestamp__lte'] = date_to

        qs = qs.filter(**filters)
        return qs


class CommandFilterForStorageTree(CommandFilter):
    asset = filters.CharFilter(method='do_nothing')
    account = filters.CharFilter(method='do_nothing')
    session = filters.CharFilter(method='do_nothing')
    risk_level = filters.NumberFilter(method='do_nothing')

    class Meta:
        model = CommandStorage
        fields = [
            'asset', 'account', 'user', 'session', 'risk_level', 'input',
            'date_from', 'date_to', 'session_id', 'risk_level', 'command_storage_id',
        ]


class CommandStorageFilter(filters.FilterSet):
    real = filters.BooleanFilter(method='filter_real')

    class Meta:
        model = CommandStorage
        fields = ['real', 'name', 'type', 'is_default']

    def filter_real(self, queryset, name, value):
        if value:
            queryset = queryset.exclude(name='null')
        return queryset
