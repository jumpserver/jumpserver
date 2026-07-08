from collections import Counter, OrderedDict, defaultdict

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.drf.reporting import BaseListReportExporter
from common.utils import i18n_trans


class FTPLogReportExporter(BaseListReportExporter):
    report_title = _('File Transfer Report')
    report_basename = 'ftp_log_report'

    def get_summary_sections(self):
        logs = self.records
        success_logs = [item for item in logs if item.is_success]
        failed_logs = [item for item in logs if not item.is_success]
        downloadable_logs = [item for item in logs if item.has_file]

        overview = OrderedDict([
            (_('Total records'), len(logs)),
            (_('Successful transfers'), len(success_logs)),
            (_('Failed transfers'), len(failed_logs)),
            (_('Success rate'), self.format_percent(len(success_logs), len(logs))),
            (_('Downloadable files'), len(downloadable_logs)),
            (_('Unique users'), len({item.user for item in logs if item.user})),
            (_('Unique assets'), len({item.asset for item in logs if item.asset})),
            (_('Unique accounts'), len({item.account for item in logs if item.account})),
            (_('Unique IPs'), len({item.remote_addr for item in logs if item.remote_addr})),
        ])

        trend_data = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
        operate_counter = Counter()
        user_counter = Counter()
        asset_counter = Counter()
        account_counter = Counter()
        ip_counter = Counter()
        filename_counter = Counter()
        time_bucket_counter = Counter({
            '00:00-05:59': 0,
            '06:00-11:59': 0,
            '12:00-17:59': 0,
            '18:00-23:59': 0,
        })

        for log in logs:
            current_time = timezone.localtime(log.date_start)
            report_date = current_time.strftime('%Y-%m-%d')
            trend = trend_data[report_date]
            trend['total'] += 1
            if log.is_success:
                trend['success'] += 1
            else:
                trend['failed'] += 1

            operate_counter[str(log.get_operate_display())] += 1

            if log.user:
                user_counter[str(log.user)] += 1
            if log.asset:
                asset_counter[str(log.asset)] += 1
            if log.account:
                account_counter[str(log.account)] += 1
            if log.remote_addr:
                ip_counter[str(log.remote_addr)] += 1
            if log.filename:
                filename_counter[str(log.filename)] += 1

            hour = current_time.hour
            if hour < 6:
                time_bucket_counter['00:00-05:59'] += 1
            elif hour < 12:
                time_bucket_counter['06:00-11:59'] += 1
            elif hour < 18:
                time_bucket_counter['12:00-17:59'] += 1
            else:
                time_bucket_counter['18:00-23:59'] += 1

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
                [_('Date'), _('Total'), _('Successful transfers'), _('Failed transfers'), _('Success rate')],
                trend_rows,
            ),
            self.build_table_section(
                _('Transfer Type Distribution'),
                [_('Operate'), _('Count')],
                self.build_counter_rows(operate_counter),
            ),
            self.build_table_section(
                _('User Top 10'),
                [_('User'), _('Count')],
                self.build_counter_rows(user_counter, top_n=10),
            ),
            self.build_table_section(
                _('Asset Top 10'),
                [_('Asset'), _('Count')],
                self.build_counter_rows(asset_counter, top_n=10),
            ),
            self.build_table_section(
                _('Account Top 10'),
                [_('Account'), _('Count')],
                self.build_counter_rows(account_counter, top_n=10),
            ),
            self.build_table_section(
                _('IP Top 10'),
                [_('Remote addr'), _('Count')],
                self.build_counter_rows(ip_counter, top_n=10),
            ),
            self.build_table_section(
                _('Filename Top 10'),
                [_('Filename'), _('Count')],
                self.build_counter_rows(filename_counter, top_n=10),
            ),
            self.build_table_section(
                _('Transfer Time Distribution'),
                [_('Time range'), _('Count')],
                self.build_counter_rows(time_bucket_counter),
            ),
        ]


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


class JobsAuditReportExporter(BaseListReportExporter):
    report_title = _('Job Audit Report')
    report_basename = 'jobs_audit_report'

    def get_summary_sections(self):
        jobs = self.records
        overview = OrderedDict([
            (_('Total records'), len(jobs)),
            (_('Periodic jobs'), len([item for item in jobs if item.is_periodic])),
            (_('One-time jobs'), len([item for item in jobs if not item.is_periodic])),
            (_('Adhoc jobs'), len([item for item in jobs if item.type == 'adhoc'])),
            (_('Playbook jobs'), len([item for item in jobs if item.type == 'playbook'])),
            (_('Unique creators'), len({
                item.creator_id for item in jobs if getattr(item, 'creator_id', None)
            })),
        ])

        created_trend = defaultdict(int)
        type_counter = Counter()
        module_counter = Counter()
        creator_counter = Counter()
        runas_policy_counter = Counter()

        for job in jobs:
            created_time = getattr(job, 'date_created', None)
            if created_time:
                report_date = timezone.localtime(created_time).strftime('%Y-%m-%d')
                created_trend[report_date] += 1

            type_counter[str(job.get_type_display())] += 1

            if job.type == 'playbook':
                module_counter[str(_('Playbook'))] += 1
            else:
                module_counter[str(job.get_module_display() or '-')] += 1

            creator = getattr(job, 'creator', None)
            if creator:
                creator_name = creator.name or creator.username
                creator_counter[str(creator_name)] += 1

            runas_policy_counter[str(job.get_runas_policy_display())] += 1

        trend_rows = [
            [date, created_trend[date]]
            for date in sorted(created_trend.keys())
        ]

        return [
            self.build_key_value_section(_('Overview'), overview.items()),
            self.build_table_section(
                _('Created Trend'),
                [_('Date'), _('Count')],
                trend_rows,
            ),
            self.build_table_section(
                _('Job Type Distribution'),
                [_('Type'), _('Count')],
                self.build_counter_rows(type_counter),
            ),
            self.build_table_section(
                _('Module Distribution'),
                [_('Module'), _('Count')],
                self.build_counter_rows(module_counter),
            ),
            self.build_table_section(
                _('Creator Top 10'),
                [_('Creator'), _('Count')],
                self.build_counter_rows(creator_counter, top_n=10),
            ),
            self.build_table_section(
                _('Run as Policy Distribution'),
                [_('Run as policy'), _('Count')],
                self.build_counter_rows(runas_policy_counter),
            ),
        ]


class JobLogAuditReportExporter(BaseListReportExporter):
    report_title = _('Job Log Report')
    report_basename = 'job_log_report'

    def get_summary_sections(self):
        logs = self.records
        success_logs = [item for item in logs if item.is_success]
        finished_logs = [item for item in logs if item.is_finished]
        unfinished_logs = [item for item in logs if not item.is_finished]

        finished_durations = [
            item.time_cost for item in finished_logs
            if getattr(item, 'time_cost', None) is not None
        ]

        overview = OrderedDict([
            (_('Total records'), len(logs)),
            (_('Successful jobs'), len(success_logs)),
            (_('Finished jobs'), len(finished_logs)),
            (_('Unfinished jobs'), len(unfinished_logs)),
            (_('Success rate'), self.format_percent(len(success_logs), len(logs))),
            (_('Unique creators'), len({
                item.creator_id for item in logs if getattr(item, 'creator_id', None)
            })),
            (_('Unique task ids'), len({str(item.task_id) for item in logs if item.task_id})),
            (_('Average duration'), '{:.2f}s'.format(
                sum(finished_durations) / len(finished_durations)
            ) if finished_durations else '0.00s'),
        ])

        trend_data = defaultdict(lambda: {'total': 0, 'success': 0, 'finished': 0, 'unfinished': 0})
        status_counter = Counter()
        job_type_counter = Counter()
        creator_counter = Counter()
        duration_bucket_counter = Counter({
            '0-10s': 0,
            '10-60s': 0,
            '60-300s': 0,
            '300s+': 0,
            'Unfinished': 0,
        })

        for log in logs:
            current_time = timezone.localtime(log.date_start or log.date_created)
            report_date = current_time.strftime('%Y-%m-%d')
            trend = trend_data[report_date]
            trend['total'] += 1
            if log.is_success:
                trend['success'] += 1
            if log.is_finished:
                trend['finished'] += 1
            else:
                trend['unfinished'] += 1

            status_counter[str(log.get_status_display())] += 1
            job_type_counter[str(log.get_job_type_display())] += 1

            creator = getattr(log, 'creator', None)
            if creator:
                creator_name = creator.name or creator.username
                creator_counter[str(creator_name)] += 1

            if not log.is_finished:
                duration_bucket_counter['Unfinished'] += 1
            elif log.time_cost < 10:
                duration_bucket_counter['0-10s'] += 1
            elif log.time_cost < 60:
                duration_bucket_counter['10-60s'] += 1
            elif log.time_cost < 300:
                duration_bucket_counter['60-300s'] += 1
            else:
                duration_bucket_counter['300s+'] += 1

        trend_rows = []
        for date in sorted(trend_data.keys()):
            item = trend_data[date]
            trend_rows.append([
                date,
                item['total'],
                item['success'],
                item['finished'],
                item['unfinished'],
                self.format_percent(item['success'], item['total']),
            ])

        return [
            self.build_key_value_section(_('Overview'), overview.items()),
            self.build_table_section(
                _('Daily Trend'),
                [_('Date'), _('Total'), _('Successful jobs'), _('Finished jobs'), _('Unfinished jobs'), _('Success rate')],
                trend_rows,
            ),
            self.build_table_section(
                _('Status Distribution'),
                [_('Status'), _('Count')],
                self.build_counter_rows(status_counter),
            ),
            self.build_table_section(
                _('Job Type Distribution'),
                [_('Job type'), _('Count')],
                self.build_counter_rows(job_type_counter),
            ),
            self.build_table_section(
                _('Creator Top 10'),
                [_('Creator'), _('Count')],
                self.build_counter_rows(creator_counter, top_n=10),
            ),
            self.build_table_section(
                _('Duration Distribution'),
                [_('Duration range'), _('Count')],
                self.build_counter_rows(duration_bucket_counter),
            ),
        ]
