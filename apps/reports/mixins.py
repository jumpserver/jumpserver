import csv
import datetime
import io
from collections import OrderedDict, defaultdict

from django.db.models import Count, F, Q, Value
from django.db.models.functions import Concat
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from openpyxl import Workbook
from rest_framework.request import Request

from accounts.const import AutomationTypes, Source
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


def _resolve_filter_usernames(filters):
    """Resolve user filter values which contain user id(s).
    Return list of username strings or None if no ids resolved.
    """
    if not filters:
        return None
    raw = filters.get('user_id')
    if not raw:
        return None
    # normalize to list
    if isinstance(raw, list):
        values = [str(x) for x in raw if x]
    else:
        values = [str(raw)]
    users = list(User.objects.filter(id__in=values))
    if users:
        return [u.username for u in users]
    return None


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

REPORT_FILTER_FIELDS = {
    'UserLoginReport': ['start', 'end', 'range_preset', 'user_id'],
    'UserChangePasswordReport': ['start', 'end', 'range_preset', 'user_id'],
    'AssetStatistics': ['start', 'end', 'range_preset', 'asset_id'],
    'AssetReport': ['start', 'end', 'range_preset', 'asset_id'],
    'AccountStatistics': ['start', 'end', 'range_preset', 'account'],
    'AccountAutomationReport': ['start', 'end', 'range_preset', 'account'],
}

CREATABLE_REPORT_TYPES = (
    'UserLoginReport',
    'UserChangePasswordReport',
    'AssetStatistics',
    'AssetReport',
    'AccountStatistics',
    'AccountAutomationReport',
)


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
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(headers)
        for row in table['rows']:
            worksheet.append([row.get(key, '') for key in keys])
        from openpyxl.writer.excel import save_virtual_workbook
        content = save_virtual_workbook(workbook)
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    response['Content-Disposition'] = f'attachment; filename="{table["filename"]}.{export}"'
    return response


def build_user_login_report(filters=None, days=7):
    filters = filters or {}
    range_info = resolve_range(
        start=filters.get('start'),
        end=filters.get('end'),
        preset=filters.get('range_preset', ''),
        days=days,
    )
    resolved_usernames = _resolve_filter_usernames(filters)
    users = User.get_org_users()
    success_qs = UserLoginLog.filter_queryset_by_org(UserLoginLog.objects.filter(status=LoginStatusChoices.success))
    failed_qs = UserLoginLog.filter_queryset_by_org(UserLoginLog.objects.filter(status=LoginStatusChoices.failed))
    if resolved_usernames:
        if isinstance(resolved_usernames, (list, tuple)):
            success_qs = success_qs.filter(username__in=resolved_usernames)
            failed_qs = failed_qs.filter(username__in=resolved_usernames)
        else:
            success_qs = success_qs.filter(username=resolved_usernames)
            failed_qs = failed_qs.filter(username=resolved_usernames)
    success_qs = filter_by_range(success_qs, 'datetime', range_info)
    failed_qs = filter_by_range(failed_qs, 'datetime', range_info)

    source_map = Source.as_dict()
    source_map.update({'password': _('Password')})
    source_data = defaultdict(int)
    for source in users.values_list('source', flat=True):
        source_data[str(source_map.get(source, source))] += 1

    success_data = defaultdict(set)
    failed_data = defaultdict(set)
    method_data = defaultdict(lambda: defaultdict(set))
    methods = set()
    for current_time, current_username, backend in success_qs.values_list('datetime', 'username', 'backend'):
        success_data[str(current_time.date())].add(current_username)
        backend_name = str(source_map.get(backend.lower(), backend))
        method_data[str(current_time.date())][backend_name].add(current_username)
        methods.add(backend_name)
    for current_time, current_username in failed_qs.values_list('datetime', 'username'):
        failed_data[str(current_time.date())].add(current_username)

    time_buckets = ['00:00-06:00', '06:00-12:00', '12:00-18:00', '18:00-24:00']
    time_metrics = {bucket: 0 for bucket in time_buckets}
    for obj in success_qs.only('datetime'):
        time_metrics[time_buckets[timezone.localtime(obj.datetime).hour // 6]] += 1

    success_metrics = [len(success_data.get(str(item), set())) for item in range_info['date_list']]
    failed_metrics = [len(failed_data.get(str(item), set())) for item in range_info['date_list']]
    method_metrics = defaultdict(list)
    for current_date in range_info['date_list']:
        current_methods = method_data.get(str(current_date), {})
        for method in methods:
            method_metrics[method].append(len(current_methods.get(method, set())))
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
    payload['user_stats']['valid'] = sum(1 for user in users if user.is_valid)
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
    filters = filters or {}
    range_info = resolve_range(
        start=filters.get('start'),
        end=filters.get('end'),
        preset=filters.get('range_preset', ''),
        days=days,
    )
    resolved_usernames = _resolve_filter_usernames(filters)
    queryset = PasswordChangeLog.filter_queryset_by_org(PasswordChangeLog.objects.all())
    if resolved_usernames:
        if isinstance(resolved_usernames, (list, tuple)):
            queryset = queryset.filter(user__in=resolved_usernames)
        else:
            queryset = queryset.filter(user=resolved_usernames)
    queryset = filter_by_range(queryset, 'datetime', range_info)
    metric_data = defaultdict(set)
    for current_time, current_user in queryset.values_list('datetime', 'user'):
        metric_data[str(current_time.date())].add(current_user)
    metrics = [len(metric_data.get(str(item), set())) for item in range_info['date_list']]
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
    filters = filters or {}
    range_info = resolve_range(
        start=filters.get('start'),
        end=filters.get('end'),
        preset=filters.get('range_preset', ''),
        days=days,
    )
    from reports.api.assets.base import group_stats
    asset_id = filters.get('asset_id', '')
    queryset = Session.objects.all()
    if asset_id:
        queryset = queryset.filter(asset_id=asset_id)
    queryset = filter_by_range(queryset, 'date_start', range_info)
    metric_data = defaultdict(set)
    for current_time, session_id in queryset.values_list('date_start', 'id'):
        metric_data[str(current_time.date())].add(session_id)
    metrics = [len(metric_data.get(str(item), set())) for item in range_info['date_list']]
    active_users_metric = defaultdict(set)
    active_assets_metric = defaultdict(set)
    for current_time, user_id, current_asset_id in queryset.values_list('date_start', 'user_id', 'asset_id'):
        report_date = str(current_time.date())
        if user_id:
            active_users_metric[report_date].add(user_id)
        if current_asset_id:
            active_assets_metric[report_date].add(current_asset_id)
    rows = [{'date': label, 'count': metrics[index]} for index, label in enumerate(range_info['date_labels'])]
    asset_ids = {str(asset_value) for asset_value in queryset.values_list('asset_id', flat=True).distinct()}
    assets = Asset.objects.filter(id__in=asset_ids)
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
                len(active_users_metric.get(str(item), set())) for item in range_info['date_list']
            ],
            'dates_metrics_total_count_active_assets': [
                len(active_assets_metric.get(str(item), set())) for item in range_info['date_list']
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


def _filter_automation_queryset_by_account(queryset, account):
    if not account:
        return queryset
    ids = []
    for automation_id, accounts in queryset.values_list('id', 'accounts'):
        if account in (accounts or []):
            ids.append(automation_id)
    return queryset.filter(id__in=ids)


def build_account_automation_report(filters=None, days=7):
    filters = filters or {}
    range_info = resolve_range(
        start=filters.get('start'),
        end=filters.get('end'),
        preset=filters.get('range_preset', ''),
        days=days,
    )
    account = filters.get('account', '')
    querysets = {
        'push': _filter_automation_queryset_by_account(PushAccountAutomation.objects.all(), account),
        'check': _filter_automation_queryset_by_account(CheckAccountAutomation.objects.all(), account),
        'backup': _filter_automation_queryset_by_account(BackupAccountAutomation.objects.all(), account),
        'collect': _filter_automation_queryset_by_account(GatherAccountsAutomation.objects.all(), account),
        'change_secret': _filter_automation_queryset_by_account(ChangeSecretAutomation.objects.all(), account),
    }
    automation_ids = []
    for queryset in querysets.values():
        automation_ids.extend(list(queryset.values_list('id', flat=True)))
    execution_queryset = AutomationExecution.objects.filter(type__in=(
        AutomationTypes.push_account,
        AutomationTypes.check_account,
        AutomationTypes.backup_account,
        AutomationTypes.gather_accounts,
        AutomationTypes.change_secret,
    ))
    if account:
        execution_queryset = execution_queryset.filter(automation_id__in=automation_ids)
    execution_queryset = filter_by_range(execution_queryset, 'date_start', range_info)
    grouped = defaultdict(lambda: defaultdict(int))
    for execution in execution_queryset:
        grouped[str(timezone.localtime(execution.date_start).date())][execution.type] += 1
    label_map = {
        AutomationTypes.push_account: str(AutomationTypes.push_account.label),
        AutomationTypes.check_account: str(AutomationTypes.check_account.label),
        AutomationTypes.backup_account: str(AutomationTypes.backup_account.label),
        AutomationTypes.gather_accounts: str(AutomationTypes.gather_accounts.label),
        AutomationTypes.change_secret: str(_('Account change secret')),
    }
    metrics = {}
    rows = []
    for report_date, label in zip(range_info['date_list'], range_info['date_labels']):
        row = {'date': label}
        current = grouped.get(str(report_date), {})
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
    success_grouped = defaultdict(int)
    failed_grouped = defaultdict(int)
    for execution in change_secret_queryset:
        report_date = str(timezone.localtime(execution.date_start).date())
        if execution.status == Status.success:
            success_grouped[report_date] += 1
        elif execution.status == Status.failed:
            failed_grouped[report_date] += 1
    payload['account_result_metrics']['dates_metrics_total_count_success'] = [
        success_grouped.get(str(item), 0) for item in range_info['date_list']
    ]
    payload['account_result_metrics']['dates_metrics_total_count_failed'] = [
        failed_grouped.get(str(item), 0) for item in range_info['date_list']
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
    filters = filters or {}
    range_info = resolve_range(
        start=filters.get('start'),
        end=filters.get('end'),
        preset=filters.get('range_preset', ''),
        days=days,
    )
    qs = Asset.objects.all()
    asset_id = filters.get('asset_id')
    if asset_id:
        qs = qs.filter(id=str(asset_id))

    all_type_dict = dict(AllTypes.choices())

    stats = qs.aggregate(
        total=Count(1),
        active=Count(1, filter=Q(is_active=True)),
        connected=Count(1, filter=Q(connectivity=Connectivity.OK)),
        zone=Count(1, filter=Q(zone__isnull=False)),
        directory_services=Count(1, filter=Q(directory_services__isnull=False)),
    )

    category_map = Category.as_dict()
    category_type_map = defaultdict(list)
    for item in AllTypes.types():
        category_type_map[str(item['category'].label)].append(item['value'])

    category_type_ids = defaultdict(lambda: defaultdict(set))
    values = qs.select_related('platform').values_list('id', 'platform__type', 'platform__category')
    for obj_id, platform_type, category in values:
        category_label = category_map.get(category, category)
        category_type_ids[category_label][platform_type].add(obj_id)

    by_type_category = defaultdict(list)
    for category_label, type_map in category_type_ids.items():
        by_type_category[category_label] = [
            {
                'label': all_type_dict.get(platform_type, platform_type),
                'type': platform_type,
                'total': len(ids),
            }
            for platform_type, ids in type_map.items()
        ]

    sorted_category_assets = OrderedDict()
    desired_order = [str(item['label']) for item in AllTypes.categories()]
    for category_label in desired_order:
        sorted_category_assets[category_label] = by_type_category.get(category_label, [])

    filtered_created = filter_by_range(qs, 'date_created', range_info)
    grouped_created = defaultdict(set)
    for created_at, obj_id in filtered_created.values_list('date_created', 'id'):
        grouped_created[str(created_at.date())].add(obj_id)

    stats.update({
        'platform_count': Platform.objects.count(),
    })

    payload = {
        'asset_stats': stats,
        'assets_by_type_category': sorted_category_assets,
        'added_asset_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_total': [len(grouped_created.get(str(item), set())) for item in range_info['date_list']],
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
    filters = filters or {}
    range_info = resolve_range(
        start=filters.get('start'),
        end=filters.get('end'),
        preset=filters.get('range_preset', ''),
        days=days,
    )
    qs = Account.objects.all()
    account = filters.get('account')
    if account:
        qs = qs.filter(username=str(account))

    stats = qs.aggregate(
        total=Count(1),
        active=Count(1, filter=Q(is_active=True)),
        connected=Count(1, filter=Q(connectivity=Connectivity.OK)),
        su_from=Count(1, filter=Q(su_from__isnull=False)),
        date_change_secret=Count(1, filter=Q(secret_reset=True)),
    )
    stats['template_total'] = AccountTemplate.objects.count()

    source_pie_data = [
        {'name': str(Source(source).label), 'value': total}
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
    grouped_changed = defaultdict(set)
    for changed_at, obj_id in filtered_changed.values_list('date_change_secret', 'id'):
        grouped_changed[str(timezone.localtime(changed_at).date())].add(obj_id)

    payload = {
        'account_stats': stats,
        'top_assets': top_assets,
        'top_version_accounts': top_version_accounts,
        'source_pie': source_pie_data,
        'by_connectivity': connectivity_data,
        'change_secret_account_metrics': {
            'dates_metrics_date': range_info['date_labels'],
            'dates_metrics_total': [len(grouped_changed.get(str(item), set())) for item in range_info['date_list']],
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