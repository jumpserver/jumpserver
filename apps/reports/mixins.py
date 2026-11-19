import csv
import datetime
import io
from collections import OrderedDict, defaultdict

from django.db import connections
from django.db.models import CharField, Count, F, Func, Min, Q, Value
from django.db.models.functions import Cast, Concat, Lower, Replace
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.request import Request

from accounts.const import AutomationTypes, Source as AccountSource
from accounts.models import (
    Account,
    AccountTemplate,
    AutomationExecution,
    BackupAccountAutomation,
    ChangeSecretAutomation,
    CheckAccountAutomation,
    GatherAccountsAutomation,
    PushAccountAutomation,
)
from assets.const import AllTypes, Category, Connectivity
from assets.models import Asset, Platform
from audits.const import LoginStatusChoices
from audits.models import PasswordChangeLog, UserLoginLog
from common.const.choices import Status
from common.utils import lazyproperty
from common.utils.timezone import local_zero_hour, local_now
from terminal.const import LoginFrom
from terminal.models import Session
from users.models import Source, User
from .const import CREATABLE_REPORT_TYPES


class DateRangeMixin:
    request: Request
    days_param = 'days'
    default_days = 1

    @lazyproperty
    def days(self) -> int:
        raw = self.request.query_params.get(self.days_param, self.default_days)
        try:
            return int(raw)
        except (ValueError, TypeError):
            return self.default_days

    @property
    def start_datetime(self):
        if self.days == 1:
            return local_zero_hour()
        return local_now() - timezone.timedelta(days=self.days)

    @property
    def date_range_bounds(self) -> tuple:
        start = self.start_datetime.date()
        end = (local_now() + timezone.timedelta(days=1)).date()
        return start, end

    @lazyproperty
    def date_range_list(self) -> list:
        return [
            (local_now() - timezone.timedelta(days=i)).date()
            for i in range(self.days - 1, -1, -1)
        ]

    def filter_by_date_range(self, queryset, field_name: str):
        start, end = self.date_range_bounds
        return queryset.filter(**{f'{field_name}__range': (start, end)})

    @lazyproperty
    def dates_metrics_date(self):
        return [date.strftime('%m-%d') for date in self.date_range_list] or ['0']


DATE_PRESET_DAYS = {
    'last_day': 1,
    'last_week': 7,
    'last_month': 30,
    'last_three_months': 90,
    'last_half_year': 180,
    'last_year': 365,
}

def parse_date(raw):
    if not raw:
        return None
    if isinstance(raw, datetime.datetime):
        return timezone.localtime(raw).date()
    if isinstance(raw, datetime.date):
        return raw
    try:
        return datetime.date.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None


def resolve_range(*, start=None, end=None, days=7, preset=''):
    if preset:
        days = DATE_PRESET_DAYS.get(preset, days)
    start_date = parse_date(start)
    end_date = parse_date(end)
    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date
    if not start_date and not end_date:
        end_date = timezone.localtime(timezone.now()).date()
        try:
            days = max(int(days or 1), 1)
        except (TypeError, ValueError):
            days = 1
        start_date = end_date - timezone.timedelta(days=max(days - 1, 0))
    elif start_date and not end_date:
        end_date = start_date
    elif end_date and not start_date:
        start_date = end_date
    if (end_date - start_date).days > 366:
        end_date = start_date + timezone.timedelta(days=366)
    start_dt = timezone.make_aware(
        datetime.datetime.combine(start_date, datetime.time.min),
        timezone.get_current_timezone()
    )
    end_dt = timezone.make_aware(
        datetime.datetime.combine(end_date + timezone.timedelta(days=1), datetime.time.min),
        timezone.get_current_timezone()
    )
    date_list = [start_date + timezone.timedelta(days=index) for index in range((end_date - start_date).days + 1)]
    return {
        'start': start_date,
        'end': end_date,
        'start_datetime': start_dt,
        'end_datetime_exclusive': end_dt,
        'date_list': date_list,
        'date_labels': [item.strftime('%m-%d') for item in date_list] or ['0'],
    }


def filter_by_range(queryset, field_name, range_info):
    return queryset.filter(**{
        f'{field_name}__gte': range_info['start_datetime'],
        f'{field_name}__lt': range_info['end_datetime_exclusive'],
    })


def export_table_response(table, export):
    if export == 'table':
        return {'columns': table['columns'], 'rows': table['rows']}
    headers = [column['label'] for column in table['columns']]
    keys = [column['key'] for column in table['columns']]
    if export == 'csv':
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for row in table['rows']:
            writer.writerow([row.get(key, '') for key in keys])
        content = buffer.getvalue().encode('utf-8-sig')
        response = HttpResponse(content, content_type='text/csv')
    else:
        from openpyxl import Workbook
        from openpyxl.cell import WriteOnlyCell

        workbook = Workbook(write_only=True)
        worksheet = workbook.create_sheet()

        def append_row(values):
            cells = []
            for value in values:
                cell = WriteOnlyCell(worksheet, value=value)
                if isinstance(value, str):
                    cell.data_type = 's'
                cells.append(cell)
            worksheet.append(cells)

        append_row(headers)
        for row in table['rows']:
            append_row(row.get(key, '') for key in keys)
        from openpyxl.writer.excel import save_virtual_workbook
        content = save_virtual_workbook(workbook)
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = f'attachment; filename="{table["filename"]}.{export}"'
    return response


class ExactText(Func):
    """Keep Python string-set semantics when counting text in the database."""
    template = '%(expressions)s'
    output_field = CharField()

    def as_mysql(self, compiler, connection, **extra_context):
        return self.as_sql(compiler, connection, template='CAST(%(expressions)s AS BINARY)', **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        return self.as_sql(compiler, connection, template='%(expressions)s COLLATE "C"', **extra_context)

    def as_sqlite(self, compiler, connection, **extra_context):
        return self.as_sql(compiler, connection, template='%(expressions)s COLLATE BINARY', **extra_context)


def aggregate_by_date(queryset, field_name, dates, *, localtime=False, **aggregates):
    """Return small daily aggregates without materializing report source rows.

    Explicit bounds preserve the caller's date basis and don't require MySQL's
    named time-zone tables. Bound each SQL statement for long report ranges.
    """
    tz = timezone.get_current_timezone() if localtime else connections[queryset.db].timezone
    results = {}
    for offset in range(0, len(dates), 7):
        batch = dates[offset:offset + 7]
        expressions = {}
        bounds = []
        for index, day in enumerate(batch):
            start = datetime.datetime.combine(day, datetime.time.min)
            end = datetime.datetime.combine(day + datetime.timedelta(days=1), datetime.time.min)
            if tz is not None:
                start = timezone.make_aware(start, tz)
                end = timezone.make_aware(end, tz)
            bounds.append((start, end))
            condition = Q(**{f'{field_name}__gte': start, f'{field_name}__lt': end})
            for name, aggregate in aggregates.items():
                expression = aggregate.copy()
                expression.filter = condition & expression.filter if expression.filter is not None else condition
                expressions[f'{name}_{index}'] = expression
        counts = queryset.filter(**{
            f'{field_name}__gte': bounds[0][0],
            f'{field_name}__lt': bounds[-1][1],
        }).order_by().aggregate(**expressions)
        for index, day in enumerate(batch):
            results[day] = {name: counts[f'{name}_{index}'] for name in aggregates}
    return results


def asset_type_category_counts(queryset):
    category_map = Category.as_dict()
    all_type_dict = dict(AllTypes.choices())
    by_category = defaultdict(list)
    grouped = queryset.order_by().annotate(
        report_type=ExactText('platform__type'), report_category=ExactText('platform__category'),
    ).values('report_type', 'report_category').annotate(total=Count('id', distinct=True))
    for item in grouped:
        category = item['report_category']
        platform_type = item['report_type']
        category = category.decode() if isinstance(category, bytes) else category
        platform_type = platform_type.decode() if isinstance(platform_type, bytes) else platform_type
        by_category[category_map.get(category, category)].append({
            'label': all_type_dict.get(platform_type, platform_type),
            'type': platform_type,
            'total': item['total'],
        })
    return OrderedDict(
        (str(item['label']), by_category.get(str(item['label']), []))
        for item in AllTypes.categories()
    )


def build_user_login_report(filters=None, days=7):
    range_info = resolve_range(days=days)
    users = User.get_org_users()
    success_qs = UserLoginLog.filter_queryset_by_org(UserLoginLog.objects.filter(status=LoginStatusChoices.success))
    failed_qs = UserLoginLog.filter_queryset_by_org(UserLoginLog.objects.filter(status=LoginStatusChoices.failed))
    success_qs = filter_by_range(success_qs, 'datetime', range_info)
    failed_qs = filter_by_range(failed_qs, 'datetime', range_info)

    source_map = Source.as_dict()
    source_map.update({'password': _('Password')})
    source_data = defaultdict(int)
    sources = (
        users.order_by().annotate(report_source=ExactText('source')).values('report_source')
        .annotate(total=Count('id', distinct=True), first_username=Min('username'))
        .order_by('first_username')
    )
    for item in sources:
        source = item['report_source']
        source = source.decode() if isinstance(source, bytes) else source
        source_data[str(source_map.get(source, source))] += item['total']

    dates = range_info['date_list']
    failed_data = aggregate_by_date(failed_qs, 'datetime', dates, total=Count(ExactText('username'), distinct=True))
    methods = defaultdict(list)
    backends = (
        success_qs.order_by().annotate(report_backend=ExactText('backend'))
        .values_list('report_backend', flat=True).distinct()
    )
    for backend in backends:
        backend = backend.decode() if isinstance(backend, bytes) else backend
        methods[str(source_map.get(backend.lower(), backend))].append(backend)
    # Labels can combine backend spellings. Aggregate each union together with
    # the total so every batch scans successful logins only once.
    success_counts = {'total': Count(ExactText('username'), distinct=True)}
    for index, backends in enumerate(methods.values()):
        success_counts[f'method_{index}'] = Count(
            ExactText('username'), distinct=True, filter=Q(report_backend__in=backends),
        )
    success_data = aggregate_by_date(
        success_qs.annotate(report_backend=ExactText('backend')), 'datetime', dates,
        **success_counts,
    )
    method_metrics = {
        method: [success_data[day][f'method_{index}'] for day in dates]
        for index, method in enumerate(methods)
    }

    time_buckets = ['00:00-06:00', '06:00-12:00', '12:00-18:00', '18:00-24:00']
    time_metrics = dict.fromkeys(time_buckets, 0)
    tz = timezone.get_current_timezone()
    for offset in range(0, len(dates), 7):
        batch = dates[offset:offset + 7]
        conditions = [Q(pk__in=[]) for _ in time_buckets]
        for day in batch:
            for index in range(4):
                midnight = datetime.datetime.combine(day, datetime.time.min)
                start = timezone.make_aware(midnight + datetime.timedelta(hours=index * 6), tz)
                end = timezone.make_aware(midnight + datetime.timedelta(hours=(index + 1) * 6), tz)
                conditions[index] |= Q(datetime__gte=start, datetime__lt=end)
        batch_start = timezone.make_aware(datetime.datetime.combine(batch[0], datetime.time.min), tz)
        batch_end = timezone.make_aware(
            datetime.datetime.combine(batch[-1] + datetime.timedelta(days=1), datetime.time.min), tz,
        )
        counts = success_qs.filter(datetime__gte=batch_start, datetime__lt=batch_end).aggregate(**{
            f'bucket_{index}': Count('id', filter=condition)
            for index, condition in enumerate(conditions)
        })
        for index, bucket in enumerate(time_buckets):
            time_metrics[bucket] += counts[f'bucket_{index}']

    success_metrics = [success_data[day]['total'] for day in dates]
    failed_metrics = [failed_data[day]['total'] for day in dates]
    rows = [{'date': label, 'success': success_metrics[index], 'failed': failed_metrics[index]}
            for index, label in enumerate(range_info['date_labels'])]
    payload = {
        'user_stats': users.aggregate(
            total=Count(1),
            first_login=Count(1, filter=Q(is_first_login=True)),
            need_update_password=Count(1, filter=Q(need_update_password=True)),
            face_vector=Count(1, filter=Q(face_vector__isnull=False)),
            not_enabled_mfa=Count(1, filter=Q(mfa_level=0)),
        ),
        'user_by_source': [{'name': key, 'value': value} for key, value in source_data.items()],
        'user_login_log_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_success_total': success_metrics,
            'dates_metrics_failure_total': failed_metrics,
        },
        'user_login_method_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_total': method_metrics,
        },
        'user_login_time_metrics': time_metrics,
    }
    payload['user_stats']['valid'] = users.filter(is_active=True).filter(
        Q(date_expired__isnull=True) | Q(date_expired__gte=timezone.now())
    ).count()
    table = {
        'filename': 'user_login_report',
        'columns': [
            {'key': 'date', 'label': 'date'},
            {'key': 'success', 'label': 'success'},
            {'key': 'failed', 'label': 'failed'},
        ],
        'rows': rows,
    }
    return payload, table, range_info


def build_user_change_password_report(filters=None, days=7):
    range_info = resolve_range(days=days)
    queryset = PasswordChangeLog.filter_queryset_by_org(PasswordChangeLog.objects.all())
    queryset = filter_by_range(queryset, 'datetime', range_info)
    metric_data = aggregate_by_date(
        queryset, 'datetime', range_info['date_list'], total=Count(ExactText('user'), distinct=True),
    )
    metrics = [metric_data[day]['total'] for day in range_info['date_list']]
    rows = [{'date': label, 'count': metrics[index]} for index, label in enumerate(range_info['date_labels'])]
    payload = {
        'total_count_change_password': {
            'total': queryset.count(),
            'user_total': queryset.values('user').distinct().count(),
            'change_by_total': queryset.values('change_by').distinct().count(),
        },
        'change_password_top10_users': list(queryset.values('user').annotate(count=Count('id')).order_by('-count')[:10]),
        'change_password_top10_change_bys': list(queryset.values('change_by').annotate(count=Count('id')).order_by('-count')[:10]),
        'user_change_password_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_total': metrics,
        },
    }
    table = {
        'filename': 'user_change_password_report',
        'columns': [
            {'key': 'date', 'label': 'date'},
            {'key': 'count', 'label': 'count'},
        ],
        'rows': rows,
    }
    return payload, table, range_info


def build_asset_activity_report(filters=None, days=7):
    range_info = resolve_range(days=days)
    from reports.api.assets.base import group_stats
    queryset = Session.objects.all()
    queryset = filter_by_range(queryset, 'date_start', range_info)
    activity_queryset = queryset.annotate(
        report_user_id=ExactText('user_id'), report_asset_id=ExactText('asset_id'),
    )
    metric_data = aggregate_by_date(
        activity_queryset, 'date_start', range_info['date_list'],
        total=Count('id', distinct=True),
        active_users=Count('report_user_id', distinct=True, filter=~Q(report_user_id='')),
        active_assets=Count('report_asset_id', distinct=True, filter=~Q(report_asset_id='')),
    )
    metrics = [metric_data[day]['total'] for day in range_info['date_list']]
    rows = [{'date': label, 'count': metrics[index]} for index, label in enumerate(range_info['date_labels'])]
    # Session IDs are text, whereas Asset IDs may use a native UUID column.
    # Normalize both sides instead of loading every distinct ID into Python.
    asset_ids = queryset.order_by().annotate(
        report_asset_id=Lower(Replace('asset_id', Value('-'), Value(''))),
    ).values('report_asset_id')
    assets = Asset.objects.annotate(
        report_asset_id=Lower(Replace(Cast('id', CharField()), Value('-'), Value(''))),
    ).filter(report_asset_id__in=asset_ids)
    payload = {
        'session_stats': queryset.aggregate(
            total=Count(1),
            asset_count=Count('asset_id', distinct=True),
            user_count=Count('user_id', distinct=True),
        ),
        'asset_login_by_type': group_stats(assets, 'label', 'platform__type', dict(AllTypes.choices())),
        'asset_login_by_from': group_stats(queryset, 'label', 'login_from', LoginFrom.as_dict()),
        'asset_login_by_protocol': group_stats(queryset, 'label', 'protocol'),
        'asset_login_log_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_total': metrics,
        },
        'user_asset_activity_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_total_count_active_users': [
                metric_data[item]['active_users'] for item in range_info['date_list']
            ],
            'dates_metrics_total_count_active_assets': [
                metric_data[item]['active_assets'] for item in range_info['date_list']
            ],
        },
    }
    table = {
        'filename': 'asset_activity_report',
        'columns': [
            {'key': 'date', 'label': 'date'},
            {'key': 'count', 'label': 'count'},
        ],
        'rows': rows,
    }
    return payload, table, range_info


def build_account_automation_report(filters=None, days=7):
    range_info = resolve_range(days=days)
    querysets = {
        'push': PushAccountAutomation.objects.all(),
        'check': CheckAccountAutomation.objects.all(),
        'backup': BackupAccountAutomation.objects.all(),
        'collect': GatherAccountsAutomation.objects.all(),
        'change_secret': ChangeSecretAutomation.objects.all(),
    }
    automation_filter = Q(pk__in=[])
    for queryset in querysets.values():
        automation_filter |= Q(automation_id__in=queryset.order_by().values('id'))
    execution_queryset = AutomationExecution.objects.filter(type__in=(
        AutomationTypes.push_account,
        AutomationTypes.check_account,
        AutomationTypes.backup_account,
        AutomationTypes.gather_accounts,
        AutomationTypes.change_secret,
    ))
    execution_queryset = execution_queryset.filter(automation_filter)
    execution_queryset = filter_by_range(execution_queryset, 'date_start', range_info)
    label_map = {
        AutomationTypes.push_account: str(AutomationTypes.push_account.label),
        AutomationTypes.check_account: str(AutomationTypes.check_account.label),
        AutomationTypes.backup_account: str(AutomationTypes.backup_account.label),
        AutomationTypes.gather_accounts: str(AutomationTypes.gather_accounts.label),
        AutomationTypes.change_secret: str(_('Account change secret')),
    }
    grouped = aggregate_by_date(
        execution_queryset, 'date_start', range_info['date_list'], localtime=True,
        **{item: Count('id', filter=Q(type=item)) for item in label_map},
    )
    metrics = {}
    rows = []
    for report_date, label in zip(range_info['date_list'], range_info['date_labels']):
        row = {'date': label}
        current = grouped.get(report_date, {})
        for item in label_map:
            value = current.get(item, 0)
            metrics.setdefault(label_map[item], []).append(value)
            row[item] = value
        rows.append(row)
    payload = {
        'automation_stats': {key: queryset.count() for key, queryset in querysets.items()},
        'execution_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'data': metrics,
        },
        'account_result_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_total_count_success': [],
            'dates_metrics_total_count_failed': [],
        },
    }
    change_secret_queryset = execution_queryset.filter(type=AutomationTypes.change_secret)
    result_counts = aggregate_by_date(
        change_secret_queryset, 'date_start', range_info['date_list'], localtime=True,
        success=Count('id', filter=Q(status=Status.success)),
        failed=Count('id', filter=Q(status=Status.failed)),
    )
    payload['account_result_metrics']['dates_metrics_total_count_success'] = [
        result_counts[item]['success'] for item in range_info['date_list']
    ]
    payload['account_result_metrics']['dates_metrics_total_count_failed'] = [
        result_counts[item]['failed'] for item in range_info['date_list']
    ]
    table = {
        'filename': 'account_automation_report',
        'columns': [
            {'key': 'date', 'label': 'date'},
            {'key': AutomationTypes.push_account, 'label': label_map[AutomationTypes.push_account]},
            {'key': AutomationTypes.check_account, 'label': label_map[AutomationTypes.check_account]},
            {'key': AutomationTypes.backup_account, 'label': label_map[AutomationTypes.backup_account]},
            {'key': AutomationTypes.gather_accounts, 'label': label_map[AutomationTypes.gather_accounts]},
            {'key': AutomationTypes.change_secret, 'label': label_map[AutomationTypes.change_secret]},
        ],
        'rows': rows,
    }
    return payload, table, range_info


def build_asset_statistics_report(filters=None, days=7):
    range_info = resolve_range(days=days)
    qs = Asset.objects.all()

    stats = qs.aggregate(
        total=Count(1),
        active=Count(1, filter=Q(is_active=True)),
        connected=Count(1, filter=Q(connectivity=Connectivity.OK)),
        zone=Count(1, filter=Q(zone__isnull=False)),
        directory_services=Count(1, filter=Q(directory_services__isnull=False)),
    )

    sorted_category_assets = asset_type_category_counts(qs)
    filtered_created = filter_by_range(qs, 'date_created', range_info)
    grouped_created = aggregate_by_date(
        filtered_created, 'date_created', range_info['date_list'], total=Count('id', distinct=True),
    )

    stats.update({
        'platform_count': Platform.objects.count(),
    })

    payload = {
        'asset_stats': stats,
        'assets_by_type_category': sorted_category_assets,
        'added_asset_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_total': [grouped_created[item]['total'] for item in range_info['date_list']],
        }
    }

    table = {
        'filename': 'asset_statistics_report',
        'columns': [
            {'key': 'metric', 'label': 'metric'},
            {'key': 'value', 'label': 'value'},
        ],
        'rows': [
            {'metric': key, 'value': value}
            for key, value in stats.items()
        ],
    }
    return payload, table, range_info


def build_account_statistics_report(filters=None, days=30):
    range_info = resolve_range(days=days)
    qs = Account.objects.all()

    stats = qs.aggregate(
        total=Count(1),
        active=Count(1, filter=Q(is_active=True)),
        connected=Count(1, filter=Q(connectivity=Connectivity.OK)),
        su_from=Count(1, filter=Q(su_from__isnull=False)),
        date_change_secret=Count(1, filter=Q(secret_reset=True)),
    )
    stats['template_total'] = AccountTemplate.objects.count()

    source_pie_data = [
        {'name': str(AccountSource(source).label), 'value': total}
        for source, total in qs.values('source').annotate(total=Count(1)).values_list('source', 'total')
    ]

    by_connectivity = (
        qs.exclude(connectivity__isnull=True)
        .values('connectivity')
        .annotate(total=Count(1))
        .order_by('connectivity')
    )
    connectivity_data = [
        {
            'label': Connectivity.as_dict().get(item['connectivity'], item['connectivity']),
            'total': item['total'],
            'connectivity': item['connectivity'],
        }
        for item in by_connectivity
    ]

    top_assets = list(
        qs.values('asset__name')
        .annotate(account_count=Count('id'))
        .order_by('-account_count')[:10]
    )

    top_version_accounts = list(
        qs.annotate(
            display_key=Concat(
                F('asset__name'),
                Value('（'),
                F('username'),
                Value('）')
            )
        ).values('display_key', 'version').order_by('-version')[:10]
    )

    filtered_changed = filter_by_range(qs.exclude(date_change_secret__isnull=True), 'date_change_secret', range_info)
    grouped_changed = aggregate_by_date(
        filtered_changed, 'date_change_secret', range_info['date_list'],
        localtime=True, total=Count('id', distinct=True),
    )

    payload = {
        'account_stats': stats,
        'top_assets': top_assets,
        'top_version_accounts': top_version_accounts,
        'source_pie': source_pie_data,
        'by_connectivity': connectivity_data,
        'change_secret_account_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_total': [grouped_changed[item]['total'] for item in range_info['date_list']],
        }
    }

    table = {
        'filename': 'account_statistics_report',
        'columns': [
            {'key': 'metric', 'label': 'metric'},
            {'key': 'value', 'label': 'value'},
        ],
        'rows': [
            {'metric': key, 'value': value}
            for key, value in stats.items()
        ],
    }
    return payload, table, range_info


def build_report_content(report_type, filters=None, days=7):
    if report_type == 'UserLoginReport':
        return build_user_login_report(filters=filters, days=days)
    if report_type == 'UserChangePasswordReport':
        return build_user_change_password_report(filters=filters, days=days)
    if report_type == 'AssetStatistics':
        return build_asset_statistics_report(filters=filters, days=days)
    if report_type == 'AssetReport':
        return build_asset_activity_report(filters=filters, days=days)
    if report_type == 'AccountStatistics':
        return build_account_statistics_report(filters=filters, days=days)
    if report_type == 'AccountAutomationReport':
        return build_account_automation_report(filters=filters, days=days)
    raise ValueError(f'Unsupported report type: {report_type}')
