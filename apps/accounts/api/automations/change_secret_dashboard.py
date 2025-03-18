# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.core.cache import cache
from django.http.response import JsonResponse
from django.utils import timezone
from rest_framework.views import APIView

from accounts.const import AutomationTypes, ChangeSecretRecordStatusChoice
from accounts.models import ChangeSecretAutomation, AutomationExecution, ChangeSecretRecord
from assets.models import Node, Asset
from common.const import Status
from common.utils import lazyproperty
from common.utils.timezone import local_zero_hour, local_now
from ops.celery import app

__all__ = ['ChangeSecretDashboardApi']


class ChangeSecretDashboardApi(APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'accounts.view_changesecretautomation',
    }

    tp = AutomationTypes.change_secret
    task_name = 'accounts.tasks.automation.execute_account_automation_task'
    ongoing_change_secret_cache_key = "ongoing_change_secret_cache_key"

    @lazyproperty
    def days(self):
        count = self.request.query_params.get('days', 1)
        return int(count)

    @property
    def days_to_datetime(self):
        if self.days == 1:
            return local_zero_hour()
        return local_now() - timezone.timedelta(days=self.days)

    def get_queryset_date_filter(self, qs, query_field='date_updated'):
        return qs.filter(**{f'{query_field}__gte': self.days_to_datetime})

    @lazyproperty
    def date_range_list(self):
        return [
            (local_now() - timezone.timedelta(days=i)).date()
            for i in range(self.days - 1, -1, -1)
        ]

    def filter_by_date_range(self, queryset, field_name):
        date_range_bounds = self.days_to_datetime.date(), (local_now() + timezone.timedelta(days=1)).date()
        return queryset.filter(**{f'{field_name}__range': date_range_bounds})

    def calculate_daily_metrics(self, queryset, date_field):
        filtered_queryset = self.filter_by_date_range(queryset, date_field)
        results = filtered_queryset.values_list(date_field, 'status')

        status_counts = defaultdict(lambda: defaultdict(int))

        for date_finished, status in results:
            date_str = str(date_finished.date())
            if status == ChangeSecretRecordStatusChoice.failed:
                status_counts[date_str]['failed'] += 1
            elif status == ChangeSecretRecordStatusChoice.success:
                status_counts[date_str]['success'] += 1

        metrics = defaultdict(list)
        for date in self.date_range_list:
            date_str = str(date)
            for status in ['success', 'failed']:
                metrics[status].append(status_counts[date_str].get(status, 0))

        return metrics

    def get_daily_success_and_failure_metrics(self):
        metrics = self.calculate_daily_metrics(self.change_secret_records_queryset, 'date_finished')
        return metrics.get('success', []), metrics.get('failed', [])

    @lazyproperty
    def change_secrets_queryset(self):
        return ChangeSecretAutomation.objects.all()

    @lazyproperty
    def change_secret_records_queryset(self):
        return ChangeSecretRecord.get_valid_records()

    def get_change_secret_asset_queryset(self):
        qs = self.change_secrets_queryset
        node_ids = qs.filter(nodes__isnull=False).values_list('nodes', flat=True).distinct()
        nodes = Node.objects.filter(id__in=node_ids)
        node_asset_ids = Node.get_nodes_all_assets(*nodes).values_list('id', flat=True)
        direct_asset_ids = qs.filter(assets__isnull=False).values_list('assets', flat=True).distinct()
        asset_ids = set(list(direct_asset_ids) + list(node_asset_ids))
        return Asset.objects.filter(id__in=asset_ids)

    def get_filtered_counts(self, qs, field=None):
        if field is None:
            return qs.count()
        return self.get_queryset_date_filter(qs, field).count()

    def get_status_counts(self, executions):
        executions = executions.filter(type=self.tp)
        total, failed, success = 0, 0, 0
        for status in executions.values_list('status', flat=True):
            total += 1
            if status in [Status.failed, Status.error]:
                failed += 1
            elif status == Status.success:
                success += 1

        return {
            'total_count_change_secret_executions': total,
            'total_count_success_change_secret_executions': success,
            'total_count_failed_change_secret_executions': failed,
        }

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        data = {}

        _all = query_params.get('all')

        if _all or query_params.get('total_count_change_secrets'):
            data['total_count_change_secrets'] = self.get_filtered_counts(
                self.change_secrets_queryset
            )

        if _all or query_params.get('total_count_periodic_change_secrets'):
            data['total_count_periodic_change_secrets'] = self.get_filtered_counts(
                self.change_secrets_queryset.filter(is_periodic=True)
            )

        if _all or query_params.get('total_count_change_secret_assets'):
            data['total_count_change_secret_assets'] = self.get_change_secret_asset_queryset().count()

        if _all or query_params.get('total_count_change_secret_status'):
            executions = self.get_queryset_date_filter(AutomationExecution.objects.all(), 'date_start')
            data.update(self.get_status_counts(executions))

        if _all or query_params.get('daily_success_and_failure_metrics'):
            success, failed = self.get_daily_success_and_failure_metrics()
            data.update({
                'dates_metrics_date': [date.strftime('%m-%d') for date in self.date_range_list] or ['0'],
                'dates_metrics_total_count_success': success,
                'dates_metrics_total_count_failed': failed,
            })

        if _all or query_params.get('total_count_ongoing_change_secret'):
            ongoing_counts = cache.get(self.ongoing_change_secret_cache_key)
            if ongoing_counts is None:
                execution_ids = []
                inspect = app.control.inspect()
                try:
                    active_tasks = inspect.active()
                except Exception:
                    active_tasks = None
                if active_tasks:
                    for tasks in active_tasks.values():
                        for task in tasks:
                            _id = task.get('id')
                            name = task.get('name')
                            tp = task.get('kwargs', {}).get('tp')
                            if name == self.task_name and tp == self.tp:
                                execution_ids.append(_id)

                snapshots = AutomationExecution.objects.filter(id__in=execution_ids).values_list('snapshot', flat=True)

                asset_ids = {asset for i in snapshots for asset in i.get('assets', [])}
                account_ids = {account for i in snapshots for account in i.get('accounts', [])}

                ongoing_counts = (len(execution_ids), len(asset_ids), len(account_ids))
                data['total_count_ongoing_change_secret'] = ongoing_counts[0]
                data['total_count_ongoing_change_secret_assets'] = ongoing_counts[1]
                data['total_count_ongoing_change_secret_accounts'] = ongoing_counts[2]
                cache.set(self.ongoing_change_secret_cache_key, ongoing_counts, 60)
            else:
                data['total_count_ongoing_change_secret'] = ongoing_counts[0]
                data['total_count_ongoing_change_secret_assets'] = ongoing_counts[1]
                data['total_count_ongoing_change_secret_accounts'] = ongoing_counts[2]

        return JsonResponse(data, status=200)
