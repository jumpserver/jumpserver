from collections import Counter, OrderedDict, defaultdict

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.drf.reporting import BaseListReportExporter
from common.utils import i18n_trans


class UserLoginLogReportExporter(BaseListReportExporter):
    report_title = _('User Login Report')
    report_basename = 'user_login_log_report'

    def get_summary_sections(self):
        logs = self.records
        total = len(logs)
        success_logs = [item for item in logs if item.status]
        failed_logs = [item for item in logs if not item.status]

        overview = OrderedDict([
            (_('Total records'), total),
            (_('Successful logins'), len(success_logs)),
            (_('Failed logins'), len(failed_logs)),
            (_('Success rate'), self.format_percent(len(success_logs), total)),
            (_('Unique users'), len({item.username for item in logs if item.username})),
            (_('Unique IPs'), len({item.ip for item in logs if item.ip})),
            (_('Unique cities'), len({item.city for item in logs if item.city})),
            (_('Unique auth backends'), len({item.backend_display for item in logs if item.backend_display})),
        ])

        trend_data = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
        type_counter = Counter()
        backend_counter = Counter()
        mfa_counter = Counter()
        time_bucket_counter = Counter({
            '00:00-05:59': 0,
            '06:00-11:59': 0,
            '12:00-17:59': 0,
            '18:00-23:59': 0,
        })
        failed_user_counter = Counter()
        failed_ip_counter = Counter()
        failed_reason_counter = Counter()

        for log in logs:
            current_time = timezone.localtime(log.datetime)
            report_date = current_time.strftime('%Y-%m-%d')
            trend = trend_data[report_date]
            trend['total'] += 1
            if log.status:
                trend['success'] += 1
            else:
                trend['failed'] += 1

            type_counter[str(log.get_type_display())] += 1
            backend_counter[str(log.backend_display or '-')] += 1
            mfa_counter[str(log.get_mfa_display())] += 1

            hour = current_time.hour
            if hour < 6:
                time_bucket_counter['00:00-05:59'] += 1
            elif hour < 12:
                time_bucket_counter['06:00-11:59'] += 1
            elif hour < 18:
                time_bucket_counter['12:00-17:59'] += 1
            else:
                time_bucket_counter['18:00-23:59'] += 1

            if not log.status:
                if log.username:
                    failed_user_counter[str(log.username)] += 1
                if log.ip:
                    failed_ip_counter[str(log.ip)] += 1
                failed_reason_counter[str(log.reason_display or log.reason or '-')] += 1

        trend_rows = []
        for date in sorted(trend_data.keys()):
            item = trend_data[date]
            trend_rows.append([
                date,
                item['total'],
                item['success'],
                item['failed'],
                self.format_percent(item['success'], item['total']),
            ])

        return [
            self.build_key_value_section(_('Overview'), overview.items()),
            self.build_table_section(
                _('Daily Trend'),
                [_('Date'), _('Total'), _('Successful logins'), _('Failed logins'), _('Success rate')],
                trend_rows,
            ),
            self.build_table_section(
                _('Login Type Distribution'),
                [_('Type'), _('Count')],
                self.build_counter_rows(type_counter),
            ),
            self.build_table_section(
                _('Auth Backend Distribution'),
                [_('Auth backend'), _('Count')],
                self.build_counter_rows(backend_counter),
            ),
            self.build_table_section(
                _('MFA Distribution'),
                [_('MFA'), _('Count')],
                self.build_counter_rows(mfa_counter),
            ),
            self.build_table_section(
                _('Login Time Distribution'),
                [_('Time range'), _('Count')],
                self.build_counter_rows(time_bucket_counter),
            ),
            self.build_table_section(
                _('Failed User Top 10'),
                [_('Username'), _('Count')],
                self.build_counter_rows(failed_user_counter, top_n=10),
            ),
            self.build_table_section(
                _('Failed IP Top 10'),
                [_('IP'), _('Count')],
                self.build_counter_rows(failed_ip_counter, top_n=10),
            ),
            self.build_table_section(
                _('Failed Reason Top 10'),
                [_('Reason'), _('Count')],
                self.build_counter_rows(failed_reason_counter, top_n=10),
            ),
        ]


class PasswordChangeLogReportExporter(BaseListReportExporter):
    report_title = _('Password Change Report')
    report_basename = 'password_change_log_report'

    def get_summary_sections(self):
        logs = self.records
        overview = OrderedDict([
            (_('Total records'), len(logs)),
            (_('Unique users'), len({item.user for item in logs if item.user})),
            (_('Unique operators'), len({item.change_by for item in logs if item.change_by})),
            (_('Unique IPs'), len({item.remote_addr for item in logs if item.remote_addr})),
        ])

        trend_data = defaultdict(int)
        user_counter = Counter()
        operator_counter = Counter()
        ip_counter = Counter()
        time_bucket_counter = Counter({
            '00:00-05:59': 0,
            '06:00-11:59': 0,
            '12:00-17:59': 0,
            '18:00-23:59': 0,
        })

        for log in logs:
            current_time = timezone.localtime(log.datetime)
            report_date = current_time.strftime('%Y-%m-%d')
            trend_data[report_date] += 1

            if log.user:
                user_counter[str(log.user)] += 1
            if log.change_by:
                operator_counter[str(log.change_by)] += 1
            if log.remote_addr:
                ip_counter[str(log.remote_addr)] += 1

            hour = current_time.hour
            if hour < 6:
                time_bucket_counter['00:00-05:59'] += 1
            elif hour < 12:
                time_bucket_counter['06:00-11:59'] += 1
            elif hour < 18:
                time_bucket_counter['12:00-17:59'] += 1
            else:
                time_bucket_counter['18:00-23:59'] += 1

        trend_rows = [
            [date, trend_data[date]]
            for date in sorted(trend_data.keys())
        ]

        return [
            self.build_key_value_section(_('Overview'), overview.items()),
            self.build_table_section(
                _('Daily Trend'),
                [_('Date'), _('Count')],
                trend_rows,
            ),
            self.build_table_section(
                _('User Top 10'),
                [_('User'), _('Count')],
                self.build_counter_rows(user_counter, top_n=10),
            ),
            self.build_table_section(
                _('Operator Top 10'),
                [_('Change by'), _('Count')],
                self.build_counter_rows(operator_counter, top_n=10),
            ),
            self.build_table_section(
                _('IP Top 10'),
                [_('Remote addr'), _('Count')],
                self.build_counter_rows(ip_counter, top_n=10),
            ),
            self.build_table_section(
                _('Change Time Distribution'),
                [_('Time range'), _('Count')],
                self.build_counter_rows(time_bucket_counter),
            ),
        ]


class OperateLogReportExporter(BaseListReportExporter):
    report_title = _('Operate Log Report')
    report_basename = 'operate_log_report'

    def get_summary_sections(self):
        logs = self.records
        overview = OrderedDict([
            (_('Total records'), len(logs)),
            (_('Unique operators'), len({item.user for item in logs if item.user})),
            (_('Unique resource types'), len({item.resource_type for item in logs if item.resource_type})),
            (_('Unique resources'), len({item.resource for item in logs if item.resource})),
            (_('Unique IPs'), len({item.remote_addr for item in logs if item.remote_addr})),
        ])

        trend_data = defaultdict(int)
        action_counter = Counter()
        resource_type_counter = Counter()
        user_counter = Counter()
        resource_counter = Counter()
        ip_counter = Counter()
        time_bucket_counter = Counter({
            '00:00-05:59': 0,
            '06:00-11:59': 0,
            '12:00-17:59': 0,
            '18:00-23:59': 0,
        })

        for log in logs:
            current_time = timezone.localtime(log.datetime)
            report_date = current_time.strftime('%Y-%m-%d')
            trend_data[report_date] += 1

            action_counter[str(log.get_action_display())] += 1
            resource_type_counter[str(getattr(log, 'resource_type_display', None) or _(log.resource_type))] += 1

            if log.user:
                user_counter[str(log.user)] += 1
            if log.resource:
                resource_counter[str(i18n_trans(log.resource))] += 1
            if log.remote_addr:
                ip_counter[str(log.remote_addr)] += 1

            hour = current_time.hour
            if hour < 6:
                time_bucket_counter['00:00-05:59'] += 1
            elif hour < 12:
                time_bucket_counter['06:00-11:59'] += 1
            elif hour < 18:
                time_bucket_counter['12:00-17:59'] += 1
            else:
                time_bucket_counter['18:00-23:59'] += 1

        trend_rows = [
            [date, trend_data[date]]
            for date in sorted(trend_data.keys())
        ]

        return [
            self.build_key_value_section(_('Overview'), overview.items()),
            self.build_table_section(
                _('Daily Trend'),
                [_('Date'), _('Count')],
                trend_rows,
            ),
            self.build_table_section(
                _('Action Distribution'),
                [_('Action'), _('Count')],
                self.build_counter_rows(action_counter),
            ),
            self.build_table_section(
                _('Resource Type Distribution'),
                [_('Resource Type'), _('Count')],
                self.build_counter_rows(resource_type_counter),
            ),
            self.build_table_section(
                _('Operator Top 10'),
                [_('User'), _('Count')],
                self.build_counter_rows(user_counter, top_n=10),
            ),
            self.build_table_section(
                _('Resource Top 10'),
                [_('Resource'), _('Count')],
                self.build_counter_rows(resource_counter, top_n=10),
            ),
            self.build_table_section(
                _('IP Top 10'),
                [_('Remote addr'), _('Count')],
                self.build_counter_rows(ip_counter, top_n=10),
            ),
            self.build_table_section(
                _('Operate Time Distribution'),
                [_('Time range'), _('Count')],
                self.build_counter_rows(time_bucket_counter),
            ),
        ]
