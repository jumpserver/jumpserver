from collections import Counter, OrderedDict, defaultdict

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.drf.reporting import BaseListReportExporter


class SessionReportExporter(BaseListReportExporter):
    report_title = _('Session Report')
    report_basename = 'session_report'

    def get_summary_sections(self):
        sessions = self.records
        success_count = finished_count = replay_count = command_count = 0
        for item in sessions:
            success_count += bool(item.is_success)
            finished_count += bool(item.is_finished)
            replay_count += bool(item.has_replay)
            command_count += bool(item.has_command)
        failed_count = len(sessions) - success_count
        active_count = len(sessions) - finished_count

        overview = OrderedDict([
            (_('Total records'), len(sessions)),
            (_('Successful sessions'), success_count),
            (_('Failed sessions'), failed_count),
            (_('Finished sessions'), finished_count),
            (_('Active sessions'), active_count),
            (_('Success rate'), self.format_percent(success_count, len(sessions))),
            (_('Sessions with replay'), replay_count),
            (_('Sessions with commands'), command_count),
            (_('Unique users'), len({item.user_id or item.user for item in sessions if item.user or item.user_id})),
            (_('Unique assets'), len({item.asset_id or item.asset for item in sessions if item.asset or item.asset_id})),
            (_('Unique terminals'), len({
                item.terminal_id for item in sessions if getattr(item, 'terminal_id', None)
            })),
        ])

        trend_data = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0, 'active': 0})
        protocol_counter = Counter()
        login_from_counter = Counter()
        user_counter = Counter()
        asset_counter = Counter()
        terminal_counter = Counter()
        ip_counter = Counter()
        duration_bucket_counter = Counter({
            '0-5m': 0,
            '5-30m': 0,
            '30-120m': 0,
            '120m+': 0,
        })

        for session in sessions:
            current_time = timezone.localtime(session.date_start)
            report_date = current_time.strftime('%Y-%m-%d')
            trend = trend_data[report_date]
            trend['total'] += 1
            if session.is_success:
                trend['success'] += 1
            else:
                trend['failed'] += 1
            if not session.is_finished:
                trend['active'] += 1

            protocol_counter[str(session.protocol or '-')] += 1
            login_from_counter[str(session.login_from_display or '-')] += 1

            if session.user:
                user_counter[str(session.user)] += 1
            if session.asset:
                asset_counter[str(session.asset)] += 1
            if session.terminal_display:
                terminal_counter[str(session.terminal_display)] += 1
            if session.remote_addr:
                ip_counter[str(session.remote_addr)] += 1

            end_time = session.date_end or timezone.now()
            duration_seconds = max(0, (end_time - session.date_start).total_seconds())
            if duration_seconds < 300:
                duration_bucket_counter['0-5m'] += 1
            elif duration_seconds < 1800:
                duration_bucket_counter['5-30m'] += 1
            elif duration_seconds < 7200:
                duration_bucket_counter['30-120m'] += 1
            else:
                duration_bucket_counter['120m+'] += 1

        trend_rows = []
        for date in sorted(trend_data.keys()):
            item = trend_data[date]
            trend_rows.append([
                date,
                item['total'],
                item['success'],
                item['failed'],
                item['active'],
                self.format_percent(item['success'], item['total']),
            ])

        return [
            self.build_key_value_section(_('Overview'), overview.items()),
            self.build_table_section(
                _('Daily Trend'),
                [_('Date'), _('Total'), _('Successful sessions'), _('Failed sessions'), _('Active sessions'), _('Success rate')],
                trend_rows,
            ),
            self.build_table_section(
                _('Protocol Distribution'),
                [_('Protocol'), _('Count')],
                self.build_counter_rows(protocol_counter),
            ),
            self.build_table_section(
                _('Login From Distribution'),
                [_('Login from'), _('Count')],
                self.build_counter_rows(login_from_counter),
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
                _('Terminal Top 10'),
                [_('Terminal'), _('Count')],
                self.build_counter_rows(terminal_counter, top_n=10),
            ),
            self.build_table_section(
                _('IP Top 10'),
                [_('Remote addr'), _('Count')],
                self.build_counter_rows(ip_counter, top_n=10),
            ),
            self.build_table_section(
                _('Duration Distribution'),
                [_('Duration range'), _('Count')],
                self.build_counter_rows(duration_bucket_counter),
            ),
        ]
