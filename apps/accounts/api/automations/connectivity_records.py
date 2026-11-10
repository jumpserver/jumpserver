"""Read-only, historical connectivity records derived from execution snapshots."""
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework.response import Response

from accounts import serializers
from assets.models import AutomationExecution
from common.drf.filters import LookupFilterBackend, SearchFilter
from .connectivity import ConnectivityExecutionViewSet

__all__ = ['ConnectivityRecordViewSet']


class RecordExecutionFilterSet(filters.FilterSet):
    execution_id = filters.UUIDFilter(field_name='id', label=_('Execution'))
    automation_id = filters.UUIDFilter(field_name='automation_id', label=_('Task'))
    type = filters.ChoiceFilter(choices=[('ping', _('Asset')), ('verify_account', _('Account'))])

    class Meta:
        model = AutomationExecution
        fields = ['execution_id', 'automation_id', 'type']


class ConnectivityRecordViewSet(ConnectivityExecutionViewSet):
    serializer_class = serializers.ConnectivityRecordSerializer
    filterset_class = RecordExecutionFilterSet
    search_fields = ('asset', 'asset_address', 'account', 'username', 'error')
    ordering_fields = ['asset', 'account', 'username', 'privileged', 'status', 'date_start', 'date_finished']
    ordering = ('-date_start',)
    page_default_limit = 15
    http_method_names = ['get', 'head', 'options']

    def list(self, request, *args, **kwargs):
        from assets.automations.base.account_results import get_execution_account_results

        # Retain the execution API's organization and per-type permission scope.
        queryset = self.get_queryset().select_related(None)
        queryset = LookupFilterBackend().filter_queryset(request, queryset, self)
        queryset = queryset.only(
            'id', 'type', 'result', 'date_start', 'date_finished', 'org_id',
        ).order_by('-date_start', '-id')
        search = SearchFilter()
        conditions = search.get_search_condition_groups(request)
        rows, unresolved = [], 0
        for execution in queryset.iterator(chunk_size=100):
            results = get_execution_account_results(execution)
            unresolved += results['unresolved']
            for account in results['rows']:
                record = {
                    **account, 'id': f"{execution.id}:{account['id']}",
                    'execution': str(execution.id), 'type': execution.type,
                    'asset': account['asset_name'], 'account': account['name'],
                    'date_start': execution.date_start, 'date_finished': execution.date_finished,
                }
                if self.matches_search(record, conditions):
                    rows.append(record)

        ordering = request.query_params.get('order', '').split(',')
        for field in reversed(ordering):
            key = field.lstrip('-')
            if key in self.ordering_fields:
                rows.sort(key=lambda row: str(row.get(key) or '').casefold(), reverse=field.startswith('-'))
        page = self.paginate_queryset(rows)
        data = self.get_serializer(page if page is not None else rows, many=True).data
        if page is None:
            return Response({'count': len(rows), 'results': data, 'unresolved': unresolved})
        response = self.get_paginated_response(data)
        response.data['unresolved'] = unresolved
        return response

    def matches_search(self, record, conditions):
        values = [str(record.get(field) or '').casefold() for field in self.search_fields]

        def contains(term):
            return any(term.casefold() in value for value in values)

        for params, match_all, is_default in conditions:
            if is_default:
                batches = SearchFilter.split_default_search_batches(params)
                if not all(any(all(contains(term) for term in terms) for terms in alternatives) for alternatives in batches):
                    return False
            else:
                groups = SearchFilter.split_search_groups(params.replace(',', ' ') if match_all else params)
                matched = [all(contains(term) for term in terms) for terms in groups]
                if matched and not (all(matched) if match_all else any(matched)):
                    return False
        return True
