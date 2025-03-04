# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.http.response import JsonResponse
from django.utils import timezone
from rest_framework.views import APIView

from accounts.const import AutomationTypes, ChangeSecretRecordStatusChoice
from accounts.models import ChangeSecretAutomation, AutomationExecution, ChangeSecretRecord
from assets.models import Node, Asset
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
    def change_secret_executions_queryset(self):
        return AutomationExecution.objects.filter(automation__type=self.tp)

    @lazyproperty
    def change_secret_records_queryset(self):
        return ChangeSecretRecord.get_valid_records().filter(execution__automation__type=self.tp)

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

    @staticmethod
    def get_status_counts(records):
        pending = ChangeSecretRecordStatusChoice.pending
        failed = ChangeSecretRecordStatusChoice.failed
        total_ids = {str(i) for i in records.exclude(status=pending).values('execution_id').distinct()}
        failed_ids = {str(i) for i in records.filter(status=failed).values('execution_id').distinct()}
        total = len(total_ids)
        failed = len(total_ids & failed_ids)
        return {
            'total_count_change_secret_executions': total,
            'total_count_success_change_secret_executions': total - failed,
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
            records = self.get_queryset_date_filter(self.change_secret_records_queryset, 'date_finished')
            data.update(self.get_status_counts(records))

        if _all or query_params.get('daily_success_and_failure_metrics'):
            success, failed = self.get_daily_success_and_failure_metrics()
            data.update({
                'dates_metrics_date': [date.strftime('%m-%d') for date in self.date_range_list] or ['0'],
                'dates_metrics_total_count_success': success,
                'dates_metrics_total_count_failed': failed,
            })

        if _all or query_params.get('total_count_ongoing_change_secret'):
            execution_ids = []
            inspect = app.control.inspect()
            active_tasks = inspect.active()
            if active_tasks:
                for tasks in active_tasks.values():
                    for task in tasks:
                        _id = task.get('id')
                        name = task.get('name')
                        tp = task.kwargs.get('tp')
                        if name == self.task_name and tp == self.tp:
                            execution_ids.append(_id)

            snapshots = self.change_secret_executions_queryset.filter(
                id__in=execution_ids).values_list('id', 'snapshot')

            asset_ids = {asset for i in snapshots for asset in i.get('assets', [])}
            account_ids = {account for i in snapshots for account in i.get('accounts', [])}
            data['total_count_ongoing_change_secret'] = len(execution_ids)
            data['total_count_ongoing_change_secret_assets'] = len(asset_ids)
            data['total_count_ongoing_change_secret_accounts'] = len(account_ids)

        return JsonResponse(data, status=200)
