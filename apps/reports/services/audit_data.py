"""Bounded, organization-aware data for the audit report document.

Totals are computed by the storage backend; only evidence samples are bounded.
An unavailable or unauthorized source is never represented by a zero count.
"""
import copy
import datetime
import hashlib
import json
import logging
from importlib import import_module

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Subquery, CharField
from django.db.models.functions import Cast, Coalesce, NullIf, Replace
from django.db.models import Value
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.const import AutomationTypes
from accounts.models import Account, AutomationExecution, ChangeSecretRecord
from assets.const import Connectivity
from assets.models import Asset
from audits.models import FTPLog, OperateLog, PasswordChangeLog, UserLoginLog
from audits.utils import construct_userlogin_usernames
from common.const.choices import Status
from orgs.utils import current_org
from reports.audit_contract import SOURCE_PERMISSIONS, THEMES
from terminal.backends import TYPE_ENGINE_MAPPING
from terminal.const import RiskLevelChoices, SessionType
from terminal.models import Command, CommandStorage, Session
from .evidence import (
    reference, replay_expression, replay_labels, connection_reason,
    error_category_expression, error_category_labels,
)

logger = logging.getLogger(__name__)
SAMPLE_LIMIT = 20
RANK_LIMIT = 10

THEME_CHAPTERS = {theme: tuple(config['chapters']) for theme, config in THEMES.items()}
CHAPTER_SOURCES = {
    'activity': ('sessions', 'commands', 'files', 'operations', 'logins'),
    'security': ('commands', 'logins', 'operations'),
    'inventory': ('assets', 'accounts'),
    'account': ('automation', 'password_changes'),
}
SOURCE_RETENTION = {
    'sessions': 'TERMINAL_SESSION_KEEP_DURATION',
    'commands': 'TERMINAL_SESSION_KEEP_DURATION',
    'logins': 'LOGIN_LOG_KEEP_DAYS',
    'files': 'FTP_LOG_KEEP_DAYS',
    'operations': 'OPERATE_LOG_KEEP_DAYS',
    'password_changes': 'PASSWORD_CHANGE_LOG_KEEP_DAYS',
}


def metric(key, label, value, unit=''):
    return {'key': key, 'label': label, 'value': value, 'unit': unit, 'help': ''}


def table(key, title, columns, rows, total=None, limit=SAMPLE_LIMIT):
    rows = list(rows)
    total = len(rows) if total is None else total
    return {
        'key': key, 'title': title,
        'columns': [{'key': key, 'label': label} for key, label in columns],
        'rows': rows, 'total': total, 'limit': limit,
        'truncated': total > len(rows), 'description': '',
    }


def display_time(value):
    if not value:
        return ''
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%Y-%m-%d %H:%M:%S')
    return str(value)


def source_result(metrics=None, tables=None, notes=None, **extra):
    return {'metrics': metrics or [], 'tables': tables or [], 'notes': notes or [], **extra}


class AuditReportBuilder:
    def __init__(self, *, user, theme, start, end, chapters=None):
        if theme not in THEME_CHAPTERS:
            raise ValueError(_('Unsupported report theme'))
        if not isinstance(start, datetime.date) or not isinstance(end, datetime.date):
            raise ValueError(_('Select a start date and an end date'))
        if start > end or (end - start).days >= 366:
            raise ValueError(_('The start date cannot be later than the end date, and the report can cover at most 366 days'))
        if end > timezone.localdate():
            raise ValueError(_('The end date cannot be later than today'))
        self.user, self.theme = user, theme
        self.start, self.end = start, end
        self.chapters = list(THEME_CHAPTERS[theme] if chapters is None else chapters)
        if not self.chapters or len(set(self.chapters)) != len(self.chapters):
            raise ValueError(_('Select report chapters without duplicates'))
        if set(self.chapters) - set(THEME_CHAPTERS[theme]):
            raise ValueError(_('The selected chapters do not belong to this report theme'))
        self.start_dt = timezone.make_aware(datetime.datetime.combine(start, datetime.time.min))
        self.end_dt = timezone.make_aware(datetime.datetime.combine(end + datetime.timedelta(days=1), datetime.time.min))
        self.generated_at = timezone.now()
        self.sources = {}
        self.data = {}

    def between(self, qs, field):
        return qs.filter(**{f'{field}__gte': self.start_dt, f'{field}__lt': self.end_dt})

    def labels(self):
        return {
            'sessions': _('Asset Sessions'), 'commands': _('Command Records'), 'logins': _('Login Logs'),
            'operations': _('Operation Logs'), 'files': _('File Transfers'), 'assets': _('Current Assets'),
            'accounts': _('Current Accounts'), 'automation': _('Account Automation Tasks'),
            'password_changes': _('Platform User Password Change Logs'),
        }

    def collect(self, key):
        if key in self.sources:
            return
        permission = SOURCE_PERMISSIONS[key]
        source = {'key': key, 'label': self.labels()[key], 'permission': permission, 'status': 'available', 'notes': []}
        self.sources[key] = source
        if not self.user.has_perm(permission):
            source.update(status='permission_denied', notes=[_('You do not have permission to view this data, so it was not queried for this report.')])
            self.data[key] = source_result()
            return
        setting_name = SOURCE_RETENTION.get(key)
        retention_days = getattr(settings, setting_name, None) if setting_name else None
        source['retention_days'] = retention_days
        coverage_start = self.start - datetime.timedelta(days=7) if key == 'logins' else self.start
        if retention_days and coverage_start < timezone.localdate() - datetime.timedelta(days=retention_days):
            source['retention_warning'] = True
            message = _('The report period or the seven-day baseline for new-city logins predates the %(days)s-day log retention period. Earlier records may have been deleted.') if key == 'logins' else _('The selected start date predates the %(days)s-day log retention period. Earlier records may have been deleted.')
            source['notes'].append(message % {'days': retention_days})
        try:
            # Under ATOMIC_REQUESTS a failed SQL statement would otherwise leave
            # PostgreSQL's outer transaction unusable for all remaining sources
            # and for saving the partial report. Isolate each source by savepoint.
            with transaction.atomic():
                result = getattr(self, 'collect_' + key)()
            self.data[key] = result
            source['notes'].extend(result.get('notes', []))
            source['status'] = result.get('status', 'available')
            source['retention_warning'] = source.get('retention_warning', False)
            if result.get('stores'):
                source['stores'] = result['stores']
        except Exception:
            # Do not leak backend addresses, queries or credentials into report snapshots.
            logger.exception('Audit report source %s failed for organization %s', key, current_org.id)
            source['status'] = 'unavailable'
            source['notes'].append(_('Data could not be read. Check the storage connection and regenerate the report; read failures are not treated as zero records.'))
            self.data[key] = source_result()

    def collect_sessions(self):
        qs = self.between(Session.objects.all(), 'date_start')
        # Historic sessions may lack an ID; use the recorded display name as a fallback.
        qs = qs.annotate(
            report_replay=replay_expression(),
            report_user=Coalesce(NullIf('user_id', Value('')), NullIf('user', Value(''))),
            report_asset=Coalesce(NullIf('asset_id', Value('')), NullIf('asset', Value(''))),
        )
        stats = qs.aggregate(
            total=Count('id'), users=Count('report_user', distinct=True),
            assets=Count('report_asset', distinct=True), failed=Count('id', filter=Q(is_success=False)),
        )
        metrics = [
            metric('sessions', _('Session Count'), stats['total'], unit=_('times')),
            metric('active_users', _('Active Users'), stats['users'], unit=_('users')),
            metric('active_assets', _('Accessed Assets'), stats['assets'], unit=_('assets')),
            metric('failed_sessions', _('Connection Failures'), stats['failed'], unit=_('times')),
        ]
        recording_labels = replay_labels()
        replay_counts = qs.order_by().values('report_replay').annotate(count=Count('id')).order_by('-count')
        tables = [table('session_recordings', _('Session Recording Status'), [('name', _('Recording Status')), ('count', _('Session Count'))],
                        [{'name': recording_labels[row['report_replay']], 'count': row['count']} for row in replay_counts])]
        failures = qs.filter(is_success=False)
        failure_groups = failures.order_by().values('error_reason').annotate(count=Count('id')).order_by('-count')
        tables.append(table('session_failure_reasons', _('Top 5 Connection Failure Reasons'), [('name', _('Recorded Reason')), ('count', _('Failure Count'))],
                            [{'name': connection_reason({**row, 'is_success': False}), 'count': row['count']} for row in failure_groups[:5]],
                            total=failure_groups.count(), limit=5))
        for field, key, title, label in (
            ('user', 'sessions_by_user', _('User Access Ranking'), _('User')),
            ('asset', 'sessions_by_asset', _('Asset Access Ranking'), _('Asset')),
            ('protocol', 'sessions_by_protocol', _('Connection Protocol Distribution'), _('Protocol')),
            ('type', 'sessions_by_type', _('Session Operation Types'), _('Type')),
        ):
            grouped = qs.order_by().values(field).annotate(count=Count('id')).order_by('-count', field)
            labels = dict(SessionType.choices) if field == 'type' else {}
            rows = [{'name': str(labels.get(row[field], row[field])) or _('Not recorded'), 'count': row['count']} for row in grouped[:RANK_LIMIT]]
            tables.append(table(key, title, [('name', label), ('count', _('Session Count'))], rows,
                                total=grouped.count(), limit=RANK_LIMIT))
        # Session.asset_id is a text column. Cast the asset UUID, rather than casting
        # historic session values (which may not be UUIDs) and failing the report.
        platform = Asset.objects.annotate(
            report_id=Replace(Cast('id', CharField()), Value('-'), Value('')),
        ).filter(
            report_id=Replace(OuterRef('asset_id'), Value('-'), Value('')),
        ).values('platform__name')[:1]
        grouped = qs.annotate(platform_name=Subquery(platform)).order_by().values('platform_name').annotate(count=Count('id')).order_by('-count')
        tables.append(table('sessions_by_platform', _('Platform Access Distribution'), [('name', _('Platform')), ('count', _('Session Count'))],
                            [{'name': row['platform_name'] or _('Asset deleted or platform not recorded'), 'count': row['count']} for row in grouped[:RANK_LIMIT]],
                            total=grouped.count(), limit=RANK_LIMIT))
        days_count = (self.end - self.start).days + 1
        interval = 'month' if days_count > 92 else 'week' if days_count > 31 else 'day'
        buckets = {}
        # Construct at most 31 buckets from dates, never from raw sessions.
        for index in range(days_count):
            day = self.start + datetime.timedelta(days=index)
            bucket = day.replace(day=1) if interval == 'month' else day - datetime.timedelta(days=day.weekday()) if interval == 'week' else day
            current = buckets.setdefault(bucket, {'start': day, 'end': day})
            current['end'] = day
        counts = {}
        for index, data in enumerate(buckets.values()):
            start_dt = timezone.make_aware(datetime.datetime.combine(data['start'], datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(data['end'] + datetime.timedelta(days=1), datetime.time.min))
            counts[f'bucket_{index}'] = Count('id', filter=Q(date_start__gte=start_dt, date_start__lt=end_dt))
        # One storage-side aggregation with explicit UTC bounds also works on
        # MySQL without named time-zone tables (TruncDate would return NULL).
        # Calculate each boundary separately so DST days retain their real length.
        counts = qs.aggregate(**counts)
        trend_rows = []
        for index, (bucket, data) in enumerate(buckets.items()):
            if interval == 'month':
                label = bucket.strftime('%Y-%m')
            elif interval == 'week':
                label = f"{data['start'].isoformat()} — {data['end'].isoformat()}"
            else:
                label = bucket.isoformat()
            trend_rows.append({'date': label, 'count': counts[f'bucket_{index}']})
        title = {'day': _('Daily Asset Session Trend'), 'week': _('Weekly Asset Session Trend'), 'month': _('Monthly Asset Session Trend')}[interval]
        tables.append(table('session_trend', title, [('date', _('Date')), ('count', _('Session Count'))],
                            trend_rows, limit=31))
        rows = [{
            'time': display_time(row['date_start']), 'user': row['user'], 'asset': row['asset'],
            'account': row['account'], 'status': _('Success') if row['is_success'] else _('Failed'),
            'replay': recording_labels[row['report_replay']], 'reason': connection_reason(row),
            'evidence': reference(row['id'], '/audit/sessions/sessions', row['org_id']),
        } for row in qs.order_by('-date_start', '-id').values(
            'id', 'date_start', 'user', 'asset', 'account', 'is_success', 'error_reason', 'report_replay', 'org_id'
        )[:SAMPLE_LIMIT]]
        tables.append(table('recent_sessions', _('Recent Asset Sessions'), [
            ('time', _('Start Time')), ('user', _('Platform User')), ('asset', _('Asset')),
            ('account', _('Asset Account')), ('status', _('Connection Result')), ('replay', _('Recording Status')),
            ('reason', _('Connection Failure Reason')), ('evidence', _('Original Session')),
        ], rows, stats['total']))
        missing = qs.filter(report_replay__in=['create_failed', 'upload_failed', 'convert_failed', 'unavailable']).count()
        metrics.append(metric('replay_attention', _('Recordings Requiring Review'), missing,
                              unit=_('times')))
        return source_result(metrics, tables)

    @staticmethod
    def es_exact(field, values):
        # Old indices may use text + keyword, new indices a direct keyword field.
        values = values if isinstance(values, list) else [values]
        return {'bool': {'should': [{'terms': {field: values}}, {'terms': {field + '.keyword': values}}], 'minimum_should_match': 1}}

    def es_filters(self, field, numeric=False):
        start, end = self.start_dt, self.end_dt
        if numeric:
            start, end = int(start.timestamp()), int(end.timestamp())
        else:
            start, end = display_time(start), display_time(end)
        filters = [{'range': {field: {'gte': start, 'lt': end}}}]
        if not current_org.is_root():
            filters.append(self.es_exact('org_id', str(current_org.id)))
        return filters

    @staticmethod
    def es_count(store, filters):
        # ES.count() and ES.filter() intentionally swallow connection failures in
        # interactive audit screens. A signed-off report must propagate them.
        response = store.es.count(index=store.query_index, body={'query': {'bool': {'filter': filters}}})
        if response.get('_shards', {}).get('failed', 0):
            raise RuntimeError('Partial Elasticsearch count')
        return response['count']

    @staticmethod
    def es_rows(store, filters, sort_field, limit=SAMPLE_LIMIT):
        response = store.es.search(index=store.query_index, body={
            'query': {'bool': {'filter': filters}}, 'size': limit,
            'sort': [{sort_field: {'order': 'desc'}}],
        })
        if response.get('timed_out') or response.get('_shards', {}).get('failed', 0):
            raise RuntimeError('Partial Elasticsearch search')
        return [hit['_source'] for hit in response['hits']['hits']]

    def collect_commands(self):
        levels = [RiskLevelChoices.warning, RiskLevelChoices.reject, RiskLevelChoices.review_reject,
                  RiskLevelChoices.review_accept, RiskLevelChoices.review_cancel]
        risk_levels = [RiskLevelChoices.warning, RiskLevelChoices.reject, RiskLevelChoices.review_reject]
        counts = {str(level): 0 for level in levels}
        rows, stores = [], []
        total = 0
        # Several storage definitions may point at the same database. Read it once.
        db = Command.objects.filter(timestamp__gte=int(self.start_dt.timestamp()), timestamp__lt=int(self.end_dt.timestamp()))
        try:
            with transaction.atomic():
                grouped = dict(db.order_by().values('risk_level').annotate(count=Count('id')).values_list('risk_level', 'count'))
                database_rows = list(db.filter(risk_level__in=risk_levels).order_by('-timestamp').values('id', 'timestamp', 'user', 'asset', 'input', 'risk_level', 'session', 'org_id')[:SAMPLE_LIMIT])
            total += sum(grouped.values())
            for level in levels:
                counts[str(level)] += grouped.get(level, 0)
            rows.extend(database_rows)
            stores.append({'type': 'database', 'status': 'available'})
        except Exception:
            logger.exception('Audit report command database unavailable')
            stores.append({'type': 'database', 'status': 'unavailable'})
        fingerprints = set()
        for storage in CommandStorage.objects.exclude(type__in=('null', 'server')):
            fingerprint = hashlib.sha256(json.dumps(storage.config, sort_keys=True, default=str).encode()).hexdigest()
            if fingerprint in fingerprints:
                continue
            fingerprints.add(fingerprint)
            try:
                engine = TYPE_ENGINE_MAPPING.get(storage.type)
                if not engine:
                    raise ValueError('Unsupported command storage')
                store = import_module(engine).CommandStore(storage.config)
                filters = self.es_filters('timestamp', numeric=True)
                storage_total = self.es_count(store, filters)
                storage_counts = {str(level): self.es_count(store, filters + [{'term': {'risk_level': int(level)}}]) for level in levels}
                storage_rows = self.es_rows(store, filters + [{'terms': {'risk_level': [int(level) for level in risk_levels]}}], 'timestamp')
                total += storage_total
                for level, count in storage_counts.items():
                    counts[level] += count
                rows.extend(storage_rows)
                stores.append({'type': storage.type, 'status': 'available'})
            except Exception:
                logger.exception('Audit report command storage unavailable: %s', storage.id)
                stores.append({'type': storage.type, 'status': 'unavailable'})
        complete = all(store['status'] == 'available' for store in stores)
        available = any(store['status'] == 'available' for store in stores)
        risk_count = sum(counts[str(level)] for level in risk_levels)
        suffix = '' if complete else _(' (available stores)')
        metrics = [metric('commands', _('Command Count') + suffix, total, unit=_('records'))]
        label_map = {
            RiskLevelChoices.warning: _('Alerted Commands'), RiskLevelChoices.reject: _('Commands Blocked by Rules'),
            RiskLevelChoices.review_reject: _('Approval-Rejected Commands'), RiskLevelChoices.review_accept: _('Approval-Approved Commands'),
            RiskLevelChoices.review_cancel: _('Approval-Canceled Commands'),
        }
        for level in levels:
            metrics.append(metric('command_' + str(int(level)), label_map[level] + suffix, counts[str(level)], unit=_('records')))
        sample = sorted(rows, key=lambda row: row.get('timestamp', 0), reverse=True)[:SAMPLE_LIMIT]
        evidence = [{
            'time': display_time(datetime.datetime.fromtimestamp(int(row['timestamp']), datetime.timezone.utc)),
            'user': row.get('user', ''), 'asset': row.get('asset', ''), 'command': row.get('input', ''),
            'action': str(label_map.get(row.get('risk_level'), row.get('risk_level', ''))),
            'record': str(row.get('id', '')),
            'session': reference(row.get('session'), '/audit/sessions/sessions', row.get('org_id', current_org.id)),
        } for row in sample]
        notes = [_('Alerts, rule blocks, and approval rejections require review; a command name or numeric level alone does not establish an attack. Ordinary queries can also be rejected by policy.'),
                 _('Command retention follows the session log cleanup settings; external storage may have its own retention policy.')]
        if not complete:
            notes.append(_('Some command stores could not be read. The figures cover available stores only and are not a complete risk total.'))
        tables = [table('command_events', _('Command Decisions Requiring Review'),
                        [('time', _('Time')), ('user', _('Platform User')), ('asset', _('Asset')),
                         ('command', _('Command')), ('action', _('Decision')), ('session', _('Related Session'))],
                        evidence, risk_count)] if available else []
        if available:
            try:
                with transaction.atomic():
                    tables.extend(self.command_approval_evidence(sample, notes))
            except Exception:
                logger.exception('Audit report approval evidence unavailable')
                notes.append(_('Approval clues could not be read. Command outcomes remain available; review the approval basis on the ticket page.'))
        return source_result(metrics if available else [], tables, notes,
                             status='available' if complete else ('partial' if available else 'unavailable'), stores=stores)

    def command_approval_evidence(self, commands, notes):
        if not self.user.has_perm('tickets.view_ticket'):
            notes.append(_('Command approval tickets were not read: ticket view permission and access to the relevant tickets are required.'))
            return []
        from tickets.models import ApplyCommandTicket
        session_ids = [item['session']['id'] for item in (
            {'session': reference(row.get('session'))} for row in commands
        ) if isinstance(item['session'], dict)]
        if not session_ids:
            return []
        qs = ApplyCommandTicket.get_user_related_tickets(self.user).filter(
            apply_from_session_id__in=session_ids, date_created__gte=self.start_dt, date_created__lt=self.end_dt,
        )
        if not current_org.is_root():
            qs = qs.filter(org_id=str(current_org.id))
        qs = qs.prefetch_related('ticket_steps__ticket_assignees').order_by('-date_created')
        rows = []
        for ticket in qs[:SAMPLE_LIMIT]:
            snapshot = ticket.rel_snapshot or {}
            decisions = [step for step in ticket.process_map if step.get('processor_display')]
            rows.append({
                'ticket': {**reference(ticket.id, '/tickets/tickets/command-confirm', ticket.org_id), 'label': ticket.serial_num or str(ticket.id)[:8]},
                'time': display_time(ticket.date_created), 'command': ticket.apply_run_command,
                'rule': str(snapshot.get('apply_from_cmd_filter_acl') or _('Historical rule name not recorded')),
                'reviewer': ', '.join(step['processor_display'] for step in decisions) or _('No reviewer recorded'),
                'opinion': _('No separate rejection reason was saved; review the ticket discussion'),
                'session': reference(ticket.apply_from_session_id, '/audit/sessions/sessions', ticket.org_id),
            })
        notes.append(_('Command logs do not store a unique approval ticket ID. "Command Approval Clues from the Same Session" lists tickets created during the period for sampled sessions that the current user can view. Match commands and times to verify the relationship.'))
        return [table('command_approvals', _('Command Approval Clues from the Same Session'),
                      [('ticket', _('Approval Ticket')), ('time', _('Request Time')), ('command', _('Requested Command')),
                       ('rule', _('Rule at the Time')), ('reviewer', _('Reviewer')), ('opinion', _('Rejection Reason')), ('session', _('Related Session'))],
                      rows, qs.count())]


    def login_queryset(self):
        qs = UserLoginLog.objects.all()
        # Always scope non-root reports, including when enterprise features are off.
        if not current_org.is_root():
            qs = qs.filter(username__in=construct_userlogin_usernames(current_org.get_members()))
        return qs

    def collect_logins(self):
        from authentication.errors import const
        qs = self.between(self.login_queryset(), 'datetime')
        lock_codes = [const.reason_block_user_login, const.reason_block_ip_login, const.reason_block_mfa]
        # Old log versions put the stable code in reason, or use acl_error.
        lock_q = Q(reason_code__in=lock_codes) | Q(reason__in=lock_codes)
        acl_q = Q(reason_code__in=[const.reason_acl_not_allow, 'acl_error']) | Q(reason__in=[const.reason_acl_not_allow, 'acl_error'])
        stats = qs.aggregate(total=Count('id'), success=Count('id', filter=Q(status=True)), failed=Count('id', filter=Q(status=False)),
                             locked=Count('id', filter=Q(status=False) & lock_q), denied=Count('id', filter=Q(status=False) & acl_q))
        metrics = [
            metric('login_success', _('Successful Logins'), stats['success'], unit=_('times')),
            metric('login_failed', _('Failed Logins'), stats['failed'], unit=_('times')),
            metric('login_locked', _('Restricted Login Records'), stats['locked'], unit=_('records')),
            metric('login_denied', _('Login Policy Denials'), stats['denied'], unit=_('records')),
        ]
        failures = qs.filter(status=False)
        rows = [{'time': display_time(row.datetime), 'user': row.username, 'ip': row.ip,
                 'city': row.city or _('Not recorded'), 'reason': str(row.reason_display) or _('Not recorded')}
                for row in failures.only('datetime', 'username', 'ip', 'city', 'reason', 'reason_code', 'reason_params').order_by('-datetime')[:SAMPLE_LIMIT]]
        tables = [table('login_failures', _('Recent Failed Logins'), [('time', _('Time')), ('user', _('User')), ('ip', _('Source IP')), ('city', _('City')), ('reason', _('Reason'))], rows, stats['failed'])]
        notes = [_('Login logs are matched to current organization members. Membership or name changes can affect historical attribution; attempts not associated with a member are excluded.'),
                 _('Failures without a stable reason code in older versions remain in the failure count but cannot be reliably classified as lockouts or policy denials.')]
        loopback_count = qs.filter(Q(ip__startswith='127.') | Q(ip='::1') | Q(ip__startswith='::ffff:127.')).count()
        if loopback_count:
            metrics.append(metric('loopback_logins', _('Loopback Address Login Records'), loopback_count,
                                  unit=_('records')))
        # Recompute city changes instead of pretending notification-only events
        # were persisted. A baseline is required, so a user's first login is not
        # labelled suspicious. Do not call the external GeoIP service here.
        unknown_cities = ['', 'Unknown', 'unknown', '未知', 'Internal', '内网', 'LAN', _('LAN'), '局域网']
        baseline = UserLoginLog.objects.filter(username=OuterRef('username'), status=True,
                                               datetime__lt=OuterRef('datetime'),
                                               datetime__gte=OuterRef('datetime') - datetime.timedelta(days=7)).exclude(city__isnull=True).exclude(city__in=unknown_cities)
        city_qs = qs.filter(status=True).exclude(city__isnull=True).exclude(city__in=unknown_cities)
        city_qs = city_qs.annotate(recent_login=Exists(baseline), known_city=Exists(baseline.filter(city=OuterRef('city')))).filter(recent_login=True, known_city=False)
        city_count = city_qs.count()
        metrics.append(metric('new_city_logins', _('New-City Login Clues'), city_count, unit=_('records')))
        city_rows = [{'time': display_time(row['datetime']), 'user': row['username'], 'ip': row['ip'], 'city': row['city']}
                     for row in city_qs.order_by('-datetime').values('datetime', 'username', 'ip', 'city')[:SAMPLE_LIMIT]]
        tables.append(table('new_city_logins', _('New-City Login Review Clues'), [('time', _('Time')), ('user', _('User')), ('ip', _('Source IP')), ('city', _('City'))], city_rows, city_count))
        notes.append(_('New-city clues are recalculated from saved city information using the seven days before the period as a baseline. Missing or deleted historical data may cause omissions.'))
        return source_result(metrics, tables, notes)

    def collect_operations(self):
        es_config = getattr(settings, 'OPERATE_LOG_ELASTICSEARCH_CONFIG', None)
        columns = [('time', _('Time')), ('user', _('User')), ('action', _('Operation')), ('type', _('Resource Type')), ('resource', _('Resource'))]
        if es_config:
            from common.plugins.es import ES
            config = copy.deepcopy(es_config)
            config.setdefault('INDEX', 'jumpserver_operate_log')
            # OperateLogStore.__init__ creates indices through pre_use_check().
            # Report generation is a read operation and must not do that.
            store = ES(config, properties={}, keyword_fields={'org_id', 'action'})
            filters = self.es_filters('datetime')
            total = self.es_count(store, filters)
            denied_filters = filters + [self.es_exact('action', 'reject')]
            denied = self.es_count(store, denied_filters)
            sample = self.es_rows(store, denied_filters, 'datetime')
            rows = [{'time': row.get('datetime', ''), 'user': row.get('user', ''), 'action': _('Rejected'), 'type': row.get('resource_type', ''), 'resource': row.get('resource', '')} for row in sample]
        else:
            qs = self.between(OperateLog.objects.all(), 'datetime')
            total = qs.count()
            rejected = qs.filter(action='reject')
            denied = rejected.count()
            rows = [{'time': display_time(row.datetime), 'user': row.user, 'action': _('Rejected'), 'type': str(row.resource_type_display), 'resource': row.resource}
                    for row in rejected.order_by('-datetime')[:SAMPLE_LIMIT]]
        return source_result([
            metric('operations', _('Platform Operation Count'), total, unit=_('times')),
            metric('policy_rejections', _('Operation Policy Denials'), denied, unit=_('records')),
        ], [table('policy_rejections', _('Policy Denial Details'), columns, rows, denied)],
            [_('Some requests with insufficient or expired permissions are not written to the operation log; this report cannot prove that no unauthorized attempts occurred.'),
             _('Operation logs are read from the current storage configuration. If storage was changed, confirm that historical records were migrated.')])

    def collect_files(self):
        qs = self.between(FTPLog.objects.all(), 'date_start')
        failures = qs.filter(is_success=False)
        stats = qs.aggregate(total=Count('id'), failed=Count('id', filter=Q(is_success=False)))
        grouped = qs.order_by().values('operate').annotate(count=Count('id')).order_by('-count')
        from audits.const import OperateChoices
        labels = dict(OperateChoices.choices)
        tables = [table('file_operations', _('File Operation Types'), [('name', _('Operation')), ('count', _('Operation Count'))],
                        [{'name': str(labels.get(row['operate'], row['operate'])), 'count': row['count']} for row in grouped], limit=20)]
        affected = failures.order_by().values('asset', 'account', 'operate').annotate(count=Count('id')).order_by('-count')
        tables.append(table('file_failure_targets', _('Top 5 Affected File Operation Targets'),
                            [('asset', _('Asset')), ('account', _('Asset Account')), ('operation', _('Operation')), ('count', _('Failure Count'))],
                            [{**row, 'operation': str(labels.get(row['operate'], row['operate']))} for row in affected[:5]],
                            total=affected.count(), limit=5))
        rows = [{
            'time': display_time(row['date_start']), 'user': row['user'], 'asset': row['asset'],
            'account': row['account'], 'operation': str(labels.get(row['operate'], row['operate'])),
            'file': row['filename'], 'record': str(row['id']),
            'session': reference(row['session'], '/audit/sessions/sessions', row['org_id']),
        } for row in failures.order_by('-date_start', '-id').values(
            'id', 'date_start', 'user', 'asset', 'account', 'operate', 'filename', 'session', 'org_id'
        )[:SAMPLE_LIMIT]]
        tables.append(table('failed_files', _('Recent Failed File Operations'),
                            [('time', _('Time')), ('user', _('Platform User')), ('asset', _('Asset')),
                             ('account', _('Asset Account')), ('operation', _('Operation')), ('file', _('File Path')), ('session', _('Related Session'))],
                            rows, stats['failed']))
        return source_result([
            metric('file_operations', _('File Operation Count'), stats['total'], unit=_('times')),
            metric('failed_file_operations', _('Failed File Operations'), stats['failed'], unit=_('times')),
            metric('file_failure_rate', _('File Operation Failure Rate'), round(stats['failed'] * 100 / stats['total'], 1) if stats['total'] else None,
                   unit='%'),
        ], tables, [_('File operation logs do not contain an error-reason field. Suspected permission or network problems are not presented as confirmed causes.')])

    def collect_assets(self):
        qs = Asset.objects.all()
        stats = qs.aggregate(total=Count('id'), active=Count('id', filter=Q(is_active=True)), connected=Count('id', filter=Q(connectivity=Connectivity.OK)))
        grouped = qs.order_by().values('platform__name').annotate(count=Count('id')).order_by('-count')
        return source_result([
            metric('assets', _('Current Asset Total'), stats['total'], unit=_('assets')),
            metric('active_assets_inventory', _('Currently Enabled Assets'), stats['active'], unit=_('assets')),
            metric('connected_assets', _('Currently Connectable Assets'), stats['connected'], unit=_('assets')),
        ], [table('asset_platforms', _('Current Asset Distribution by Platform'), [('name', _('Platform')), ('count', _('Asset Count'))],
                  [{'name': row['platform__name'] or _('Not recorded'), 'count': row['count']} for row in grouped[:RANK_LIMIT]], total=grouped.count(), limit=RANK_LIMIT)])

    def collect_accounts(self):
        qs = Account.objects.all()
        stats = qs.aggregate(total=Count('id'), active=Count('id', filter=Q(is_active=True)), connected=Count('id', filter=Q(connectivity=Connectivity.OK)))
        grouped = qs.order_by().values('asset__name').annotate(count=Count('id')).order_by('-count')
        return source_result([
            metric('accounts', _('Current Asset Accounts'), stats['total'], unit=_('accounts')),
            metric('active_accounts', _('Currently Enabled Accounts'), stats['active'], unit=_('accounts')),
            metric('connected_accounts', _('Currently Connectable Accounts'), stats['connected'], unit=_('accounts')),
        ], [table('accounts_by_asset', _('Asset Account Count Ranking'), [('name', _('Asset')), ('count', _('Account Count'))],
                  [{'name': row['asset__name'] or _('Not recorded'), 'count': row['count']} for row in grouped[:RANK_LIMIT]], total=grouped.count(), limit=RANK_LIMIT)])

    def collect_automation(self):
        types = [AutomationTypes.push_account, AutomationTypes.check_account, AutomationTypes.backup_account,
                 AutomationTypes.gather_accounts, AutomationTypes.change_secret, AutomationTypes.verify_account]
        qs = self.between(AutomationExecution.objects.filter(type__in=types), 'date_start')
        stats = qs.aggregate(total=Count('id'), success=Count('id', filter=Q(status=Status.success)),
                             failed=Count('id', filter=Q(status__in=[Status.failed, Status.error])),
                             pending=Count('id', filter=Q(status__in=[Status.ready, Status.pending, Status.running])))
        metrics = [
            metric('automation_executions', _('Account Task Executions'), stats['total'], unit=_('times')),
            metric('automation_success', _('Successful Executions'), stats['success'], unit=_('times')),
            metric('automation_failed', _('Failed or Errored Executions'), stats['failed'], unit=_('times')),
            metric('automation_pending', _('Incomplete Executions'), stats['pending'], unit=_('times')),
        ]
        labels = dict(AutomationTypes.choices)
        grouped = qs.order_by().values('type', 'status').annotate(count=Count('id')).order_by('type', 'status')
        status_labels = dict(Status.choices)
        rows = [{'name': str(labels.get(row['type'], row['type'])), 'status': str(status_labels.get(row['status'], row['status'])), 'count': row['count']} for row in grouped]
        tables = [table('automation_results', _('Account Task Types and Results'), [('name', _('Task Type')), ('status', _('Result')), ('count', _('Execution Count'))], rows, limit=100)]
        failures = qs.filter(status__in=[Status.failed, Status.error])
        # Never deserialize encrypted execution snapshots: those contain secrets.
        execution_paths = {
            AutomationTypes.change_secret: '/pam/account-change-secret/executions',
            AutomationTypes.backup_account: '/pam/account-backup/executions',
            AutomationTypes.push_account: '/pam/account-push/executions',
            AutomationTypes.gather_accounts: '/pam/account-discovery/executions',
            AutomationTypes.check_account: '/pam/check/executions',
        }
        rows = [{
            'time': display_time(row['date_start']),
            'id': reference(row['id'], execution_paths[row['type']], row['org_id']) if row['type'] in execution_paths else str(row['id']),
            'name': str(labels.get(row['type'], row['type'])),
            'status': str(status_labels.get(row['status'], row['status'])),
        } for row in failures.order_by('-date_start').values('id', 'type', 'status', 'date_start', 'org_id')[:SAMPLE_LIMIT]]
        tables.append(table('failed_automations', _('Recent Failed Account Tasks'), [('time', _('Start Time')), ('name', _('Task Type')), ('status', _('Result')), ('id', _('Original Execution Record'))], rows, stats['failed']))
        metrics.append(metric('automation_failure_rate', _('Task Failure or Error Rate'),
                              round(stats['failed'] * 100 / stats['total'], 1) if stats['total'] else None,
                              unit='%'))
        notes = [_('Task-level results differ from account-level results. A task may process multiple accounts; review each account in the execution details.'),
                 _('Original record links require sign-in and the relevant permissions. Tasks without a detail page retain their full execution ID; deleted records may no longer be available.')]
        detail_metrics, detail_tables, detail_notes = [], [], []
        try:
            with transaction.atomic():
                self.change_secret_evidence(qs, detail_metrics, detail_tables, detail_notes)
            metrics.extend(detail_metrics)
            tables.extend(detail_tables)
            notes.extend(detail_notes)
        except Exception:
            logger.exception('Audit report change-secret evidence unavailable')
            notes.append(_('Account-level password-change details could not be read. Task totals remain available; check execution details for the affected scope.'))
        return source_result(metrics, tables, notes)

    def change_secret_evidence(self, executions, metrics, tables, notes):
        if not self.user.has_perm('accounts.view_changesecretrecord'):
            notes.append(_('Account-level password-change errors and impact were not read: permission to view password-change records is required.'))
            return
        records = ChangeSecretRecord.objects.filter(execution_id__in=Subquery(executions.values('id')))
        failures = records.filter(status__in=['failed', 'unverified'])
        impact = failures.aggregate(total=Count('id'), assets=Count('asset_id', distinct=True), accounts=Count('account_id', distinct=True))
        if not impact['total']:
            notes.append(_('No failed or unverified password-change account records are available for the selected tasks. This cannot establish causes or affected account counts for other tasks.'))
            return
        metrics.extend([
            metric('change_secret_affected_assets', _('Assets with Password Changes Requiring Review'), impact['assets'], unit=_('assets')),
            metric('change_secret_affected_accounts', _('Accounts with Password Changes Requiring Review'), impact['accounts'], unit=_('accounts')),
        ])
        labels = error_category_labels()
        categorized = failures.annotate(report_reason=error_category_expression())
        groups = categorized.order_by().values('report_reason').annotate(count=Count('id')).order_by('-count')
        tables.append(table('change_secret_reasons', _('Top 5 Password-Change Error Clues'), [('name', _('Error Clue Category')), ('count', _('Account Record Count'))],
                            [{'name': labels[row['report_reason']], 'count': row['count']} for row in groups[:5]],
                            total=groups.count(), limit=5))
        later = ChangeSecretRecord.objects.filter(
            account_id=OuterRef('account_id'), asset_id=OuterRef('asset_id'),
            execution__org_id=OuterRef('execution__org_id'), status='success',
            date_finished__gt=OuterRef('date_finished'), date_finished__lte=self.generated_at,
        )
        rows = [{
            'time': display_time(row['date_finished']), 'asset': row['asset__name'] or _('Asset deleted'),
            'account': row['account__username'] or _('Account deleted'), 'reason': labels[row['report_reason']],
            'followup': _('Later success recorded; review required') if row['later_success'] else _('No later success found; manual review required'),
            'execution': reference(row['execution_id'], '/pam/account-change-secret/executions', row['execution__org_id']),
        } for row in categorized.annotate(later_success=Exists(later)).order_by('-date_finished', '-id').values(
            'date_finished', 'asset__name', 'account__username', 'report_reason', 'later_success', 'execution_id', 'execution__org_id'
        )[:SAMPLE_LIMIT]]
        tables.append(table('change_secret_followup', _('Password-Change Accounts Requiring Review'),
                            [('time', _('Record Time')), ('asset', _('Asset')), ('account', _('Account')),
                             ('reason', _('Error Clue')), ('followup', _('Follow-up Record')), ('execution', _('Execution Record'))], rows, impact['total']))


    def collect_password_changes(self):
        qs = PasswordChangeLog.objects.all()
        if not current_org.is_root():
            from audits.models import user_display_expression
            names = current_org.get_members().annotate(display=user_display_expression()).values('display')
            qs = qs.filter(user__in=Subquery(names))
        qs = self.between(qs, 'datetime')
        count = qs.count()
        rows = [{'time': display_time(row['datetime']), 'user': row['user'], 'operator': row['change_by']}
                for row in qs.order_by('-datetime').values('datetime', 'user', 'change_by')[:SAMPLE_LIMIT]]
        return source_result([
            metric('platform_password_changes', _('Platform User Password Changes'), count, unit=_('times')),
        ], [table('platform_password_changes', _('Recent Platform User Password Changes'), [('time', _('Time')), ('user', _('User')), ('operator', _('Operator'))], rows, count)],
            [_('Platform user password-change logs are matched by current organization member display names; membership changes can affect historical attribution.')])

    def conclusions(self):
        values = {}
        for key, data in self.data.items():
            if self.sources[key]['status'] == 'available':
                values.update({item['key']: item['value'] for item in data['metrics']})
        conclusions = []
        if 'activity' in self.topic_chapters and 'sessions' in values:
            conclusions.append(_('%(sessions)s asset sessions were recorded during the period, involving %(users)s users and %(assets)s assets.') % {
                'sessions': values['sessions'], 'users': values['active_users'], 'assets': values['active_assets']})
        if 'activity' in self.topic_chapters:
            if values.get('failed_file_operations'):
                conclusions.append(_('%(failed)s / %(total)s file operations failed (%(rate)s%%). Prioritize affected assets, accounts, and paths; the log does not record a specific cause, so check session and component logs.') % {
                    'failed': values['failed_file_operations'], 'total': values['file_operations'], 'rate': values['file_failure_rate']})
            if values.get('failed_sessions'):
                conclusions.append(_('%(count)s asset connections failed. Check network, credentials, and access conditions using connection failure reasons and original sessions; unsupported recording is not a connection failure.') % {'count': values['failed_sessions']})
            if values.get('replay_attention'):
                conclusions.append(_('%(count)s completed successful sessions require recording review. Check recording creation, upload, and storage to avoid gaps in audit evidence.') % {'count': values['replay_attention']})
            if values.get('sessions') and values.get('active_users') == 1:
                conclusions.append(_('Asset sessions are concentrated on one platform user. Verify whether this is a test scenario and whether production actions can be traced to individuals; one recorded user does not prove a shared account.'))
        if values.get('loopback_logins'):
            conclusions.append(_('%(count)s platform login records use loopback source addresses. Check local access or the proxy chain; this alone does not establish an incorrect client IP.') % {'count': values['loopback_logins']})
        command_risk = sum(values.get('command_' + str(level), 0) for level in [4, 5, 6])
        if 'security' in self.topic_chapters and command_risk:
            conclusions.append(_('%(count)s alerted or rejected commands were recorded. Review their purpose and approval basis in the session context.') % {'count': command_risk})
        if 'security' in self.topic_chapters and (values.get('login_locked', 0) or values.get('login_denied', 0)):
            conclusions.append(_('Restricted logins or policy denials were recorded. Verify that the source, user identity, and access policy are expected.'))
        if 'security' in self.topic_chapters and values.get('new_city_logins', 0):
            conclusions.append(_('%(count)s new-city login clues were found. Check travel, proxies, or changes in city identification; a city change alone does not establish an attack.') % {'count': values['new_city_logins']})
        if 'security' in self.topic_chapters and values.get('policy_rejections', 0):
            conclusions.append(_('The operation log contains %(count)s policy denials. Check the denied resources and policies in the audit details.') % {'count': values['policy_rejections']})
        if 'account' in self.topic_chapters and values.get('automation_failed', 0):
            conclusions.append(_('%(failed)s / %(total)s account task executions failed or errored (%(rate)s%%). Prioritize the password-change account review list. Accounts without a later success need manual review; check original execution logs for other task causes.') % {
                'failed': values['automation_failed'], 'total': values['automation_executions'], 'rate': values['automation_failure_rate']})
        if 'account' in self.topic_chapters and values.get('platform_password_changes', 0):
            conclusions.append(_('%(count)s platform user password changes were recorded. Review the operators and change rationale as needed.') % {'count': values['platform_password_changes']})
        if any(source['status'] != 'available' or source.get('retention_warning') for source in self.sources.values()):
            conclusions.append(_('Some data was unavailable due to permissions, read failures, or retention limits. Conclusions use available records only; obtain missing data before finalizing them.'))
        if not conclusions:
            conclusions.append(_('Available records are insufficient for a specific conclusion. Review the report scope and audit details manually.'))
        return conclusions

    def build(self):
        topic_chapters = [chapter for chapter in self.chapters if chapter in CHAPTER_SOURCES]
        # An overview-only report still needs the selected theme's data. A custom
        # subset of substantive chapters never silently collects other chapters.
        if not topic_chapters and any(chapter in self.chapters for chapter in ('overview', 'conclusion')):
            topic_chapters = [chapter for chapter in THEME_CHAPTERS[self.theme] if chapter in CHAPTER_SOURCES]
        self.topic_chapters = topic_chapters
        for chapter in topic_chapters:
            for key in CHAPTER_SOURCES[chapter]:
                self.collect(key)
        conclusions = self.conclusions()
        titles = {'scope': _('Report Scope'), 'overview': _('Key Overview'), 'activity': _('Operations Activity Analysis'),
                  'security': _('Security Event Analysis'), 'inventory': _('Asset and Account Overview'),
                  'account': _('Account Operations Analysis'), 'conclusion': _('Management Summary and Recommendations')}
        sections = []
        for chapter in self.chapters:
            section = {'key': chapter, 'title': titles[chapter], 'description': '',
                       'status': 'available', 'metrics': [], 'tables': [], 'notes': []}
            if chapter in CHAPTER_SOURCES:
                sources = CHAPTER_SOURCES[chapter]
                for key in sources:
                    section['metrics'].extend(copy.deepcopy(self.data[key]['metrics']))
                    section['tables'].extend(copy.deepcopy(self.data[key]['tables']))
                    section['notes'].extend(self.sources[key]['notes'])
                    if self.sources[key]['status'] != 'available':
                        section['notes'].append(_('%(source)s: %(message)s') % {
                            'source': self.sources[key]['label'],
                            'message': _('View permission unavailable') if self.sources[key]['status'] == 'permission_denied' else _('Data incomplete or could not be read'),
                        })
                statuses = [self.sources[key]['status'] for key in sources]
                section['status'] = 'available' if all(status == 'available' for status in statuses) else ('partial' if any(status in ('available', 'partial') for status in statuses) else 'unavailable')
                # Keep operational and risk views focused, while using the same
                # collected source data and queries in an integrated report.
                if chapter == 'activity':
                    section['tables'] = [item for item in section['tables'] if item['key'] not in ('command_events', 'command_approvals', 'login_failures', 'new_city_logins', 'policy_rejections')]
                    section['metrics'] = [item for item in section['metrics'] if not item['key'].startswith('command_') and item['key'] not in ('login_failed', 'login_locked', 'login_denied', 'new_city_logins', 'policy_rejections')]
                if chapter == 'security':
                    section['metrics'] = [item for item in section['metrics'] if item['key'] not in ('operations', 'commands', 'login_success')]
            elif chapter == 'overview':
                preferred = ('sessions', 'active_users', 'active_assets', 'commands', 'login_failed', 'command_5', 'assets', 'accounts', 'automation_executions', 'automation_failed', 'file_operations', 'operations', 'login_success', 'command_4', 'command_6', 'login_locked', 'login_denied', 'new_city_logins', 'policy_rejections', 'active_assets_inventory', 'active_accounts', 'connected_accounts', 'automation_success', 'platform_password_changes')
                chapter_metrics = {
                    'activity': {'sessions', 'active_users', 'active_assets', 'commands', 'file_operations', 'operations', 'login_success'},
                    'security': {'login_failed', 'command_5', 'command_4', 'command_6', 'login_locked', 'login_denied', 'new_city_logins', 'policy_rejections'},
                    'inventory': {'assets', 'accounts', 'active_assets_inventory', 'active_accounts', 'connected_accounts'},
                    'account': {'automation_executions', 'automation_failed', 'automation_success', 'platform_password_changes'},
                }
                allowed = set().union(*(chapter_metrics[key] for key in topic_chapters))
                metrics_by_key = {item['key']: item for data in self.data.values() for item in data['metrics']}
                section['metrics'] = [copy.deepcopy(metrics_by_key[key]) for key in preferred if key in metrics_by_key and key in allowed][:10]
                section['notes'] = [_('Data unavailable due to missing permissions or read errors is not displayed as zero. See the report coverage information.')]
                if any(source['status'] != 'available' for source in self.sources.values()):
                    section['status'] = 'partial'
            elif chapter == 'scope':
                section['tables'] = [table('scope', _('Report Information'), [('name', _('Item')), ('value', _('Content'))], [
                    {'name': _('Organization'), 'value': str(current_org.name)},
                    {'name': _('Report Period'), 'value': f'{self.start.isoformat()} — {self.end.isoformat()}'},
                    {'name': _('Reporting Time Zone'), 'value': timezone.get_current_timezone_name()},
                    {'name': _('Generation Time'), 'value': display_time(self.generated_at)},
                ])]
                section['notes'] = [_("The period includes the full start and end dates; today's data is counted through report generation time."),
                                    _('Log totals are counted by storage; details show up to the latest 20 records and rankings up to the top 10 items.')]
            elif chapter == 'conclusion':
                section['notes'] = conclusions
            sections.append(section)
        sources = list(self.sources.values())
        partial = any(source['status'] != 'available' or source.get('retention_warning') for source in sources)
        return {
            'schema_version': 1, 'theme': self.theme,
            'range': {'start': self.start.isoformat(), 'end': self.end.isoformat(), 'days': (self.end - self.start).days + 1, 'timezone': timezone.get_current_timezone_name()},
            'generated_at': self.generated_at.isoformat(),
            'organization': {'id': str(current_org.id), 'name': str(current_org.name)},
            'sections': sections, 'conclusions': conclusions,
            'coverage': {
                'status': 'partial' if partial else 'available', 'sources': sources,
                'notes': [],
            },
        }


def generate_report_data(*, user, theme, start, end, chapters=None):
    """Return JSON-ready report content under the caller's current organization."""
    return AuditReportBuilder(user=user, theme=theme, start=start, end=end, chapters=chapters).build()
