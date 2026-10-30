"""Organization-aware data for the audit report document.

Grouped distributions are complete; only raw evidence samples are bounded.
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
from django.db.models import Count, Exists, OuterRef, Q, Subquery, CharField, Case, When, IntegerField
from django.db.models.functions import Cast, Coalesce, Concat, NullIf
from django.db.models import Value
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.const import AutomationTypes
from accounts.models import Account, AccountRisk, AutomationExecution, ChangeSecretRecord, RiskChoice
from assets.const import Connectivity
from assets.models import Asset
from audits.models import FTPLog, OperateLog, PasswordChangeLog, UserLoginLog
from common.const.choices import ConfirmOrIgnore, Status
from orgs.utils import current_org
from reports.audit_contract import SOURCE_PERMISSIONS, THEMES
from terminal.backends import TYPE_ENGINE_MAPPING
from terminal.const import RiskLevelChoices, SessionType
from terminal.models import Command, CommandStorage, Session
from .evidence import (
    reference, replay_expression, replay_labels, connection_reason,
    error_category_expression, error_category_labels,
)
from .queries import es_counts, session_platform_counts

logger = logging.getLogger(__name__)
SAMPLE_LIMIT = 20

THEME_CHAPTERS = {theme: tuple(config['chapters']) for theme, config in THEMES.items()}
CHAPTER_SOURCES = {
    'activity': ('sessions', 'commands', 'files', 'operations', 'logins'),
    'security': ('commands', 'logins', 'operations'),
    'inventory': ('assets', 'accounts'),
    'account': ('automation', 'password_changes'),
    'account_health': ('account_risks',),
    'remediation': ('account_risks', 'sessions', 'commands', 'logins', 'operations', 'files', 'automation'),
}


def metric(key, label, value, unit='', state=None):
    return {'key': key, 'label': label, 'value': value, 'unit': unit, 'help': '',
            'state': state or ('unavailable' if value is None else 'value')}


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


def source_result(metrics=None, tables=None, **extra):
    return {'metrics': metrics or [], 'tables': tables or [], 'notes': [], **extra}


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
        self.chapters = [chapter for chapter in self.chapters if chapter not in {'scope', 'assessment'}]
        if not self.chapters:
            raise ValueError(_('Select at least one chapter containing statistical data.'))
        if set(self.chapters) - set(THEME_CHAPTERS[theme]):
            raise ValueError(_('The selected chapters do not belong to this report theme'))
        self.start_dt = timezone.make_aware(datetime.datetime.combine(start, datetime.time.min))
        self.end_dt = timezone.make_aware(datetime.datetime.combine(end + datetime.timedelta(days=1), datetime.time.min))
        self.generated_at = timezone.now()
        self.sources = {}
        self.data = {}

    def between(self, qs, field):
        return qs.filter(**{f'{field}__gte': self.start_dt, f'{field}__lt': self.end_dt})

    def sources_for_chapter(self, chapter):
        return tuple(key for key in CHAPTER_SOURCES[chapter] if key in THEMES[self.theme]['sources'])

    @property
    def needs_security_details(self):
        chapters = getattr(self, 'topic_chapters', self.chapters)
        if not set(chapters).intersection(CHAPTER_SOURCES):
            chapters = THEME_CHAPTERS[self.theme]
        return bool(set(chapters).intersection({'security', 'remediation'}))

    def evidence(self, value, path='', org_id=''):
        permissions = {
            '/audit/sessions/sessions': 'terminal.view_session',
            '/audit/audits/login-logs': 'audits.view_userloginlog',
            '/audit/audits/operate-logs': 'audits.view_operatelog',
            '/tickets/tickets/command-confirm': 'tickets.view_ticket',
            '/pam/security/account-change-secret/executions': 'accounts.view_changesecretexecution',
            '/pam/automations/account-backup/executions': 'accounts.view_backupaccountexecution',
            '/pam/automations/account-push/executions': 'accounts.view_pushaccountexecution',
            '/pam/automations/account-discovery/executions': 'accounts.view_gatheraccountsexecution',
            '/pam/security/check/executions': 'accounts.view_checkaccountexecution',
        }
        if path and not self.user.has_perm(permissions[path]):
            path = ''
        return reference(value, path, org_id)

    @staticmethod
    def action_table(key, title, rows, total, asset_label=None, account_label=None, platform_user=False):
        columns = [('time', _('Time'))]
        if platform_user:
            columns.append(('user', _('Platform User')))
        return table(key, title, columns + [
            ('asset', asset_label or _('Asset')), ('account', account_label or _('Account')),
            ('issue', _('Issue')), ('status', _('Status')), ('next_step', _('Next Step')),
            ('evidence', _('Original Record')),
        ], rows, total)

    def labels(self):
        return {
            'sessions': _('Asset Sessions'), 'commands': _('Command Records'), 'logins': _('Login Logs'),
            'operations': _('Operation Logs'), 'files': _('File Transfers'), 'assets': _('Current Assets'),
            'accounts': _('Current Accounts'), 'automation': _('Account Automation Tasks'),
            'password_changes': _('Platform User Password Change Logs'),
            'account_risks': _('Current Account Risks'),
        }

    def collect(self, key):
        if key in self.sources:
            return
        permission = SOURCE_PERMISSIONS[key]
        source = {'key': key, 'label': self.labels()[key], 'permission': permission, 'status': 'available',
                  'notes': [], 'warnings': [], 'has_issues': False}
        self.sources[key] = source
        if not self.user.has_perm(permission):
            source.update(status='permission_denied', has_issues=True)
            self.data[key] = source_result()
            return
        try:
            # Under ATOMIC_REQUESTS a failed SQL statement would otherwise leave
            # PostgreSQL's outer transaction unusable for all remaining sources
            # and for saving the partial report. Isolate each source by savepoint.
            with transaction.atomic():
                result = getattr(self, 'collect_' + key)()
            self.data[key] = result
            source['warnings'] = result.get('warnings', [])
            source['status'] = result.get('status', 'available')
            source['has_issues'] = source['status'] != 'available' or bool(source['warnings'])
            for item in result['tables'] + result.get('actions', []):
                item.setdefault('source_status', source['status'])
            if result.get('stores'):
                source['stores'] = result['stores']
        except Exception:
            # Do not leak backend addresses, queries or credentials into report snapshots.
            logger.exception('Audit report source %s failed for organization %s', key, current_org.id)
            source['status'] = 'unavailable'
            source['has_issues'] = True
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
            rows = [{'name': str(labels.get(row[field], row[field])) or _('Not recorded'), 'count': row['count']} for row in grouped.iterator()]
            tables.append(table(key, title, [('name', label), ('count', _('Session Count'))], rows,
                                limit=None))
        platforms = session_platform_counts(qs, Asset.objects.all())
        tables.append(table('sessions_by_platform', _('Platform Access Distribution'), [('name', _('Platform')), ('count', _('Session Count'))],
                            [{'name': name or _('Asset deleted or platform not recorded'), 'count': count}
                             for name, count in platforms.most_common()],
                            limit=None))
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
            'ip': row['remote_addr'] or _('Not recorded'), 'protocol': row['protocol'],
            'account': row['account'], 'status': _('Success') if row['is_success'] else _('Failed'),
            'replay': recording_labels[row['report_replay']], 'reason': connection_reason(row),
            'evidence': self.evidence(row['id'], '/audit/sessions/sessions', row['org_id']),
        } for row in qs.order_by('-date_start', '-id').values(
            'id', 'date_start', 'user', 'asset', 'account', 'remote_addr', 'protocol', 'is_success', 'error_reason', 'report_replay', 'org_id'
        )[:SAMPLE_LIMIT]]
        tables.append(table('recent_sessions', _('Recent Asset Sessions'), [
            ('time', _('Start Time')), ('user', _('Platform User')), ('asset', _('Asset')),
            ('account', _('Asset Account')), ('ip', _('Source IP')), ('protocol', _('Protocol')),
            ('status', _('Connection Result')), ('replay', _('Recording Status')),
            ('reason', _('Connection Failure Reason')), ('evidence', _('Original Session')),
        ], rows, stats['total']))
        missing = sum(row['count'] for row in replay_counts
                      if row['report_replay'] in {'create_failed', 'upload_failed', 'convert_failed', 'unavailable'})
        metrics.append(metric('replay_attention', _('Recordings Requiring Review'), missing,
                              unit=_('times')))
        actions = []
        if 'remediation' in self.chapters:
            failure_rows = [{
                'time': display_time(row['date_start']), 'user': row['user'], 'asset': row['asset'], 'account': row['account'],
                'issue': connection_reason(row), 'status': _('Failed'),
                'next_step': _('Check connection conditions and the original session before retrying.'),
                'evidence': self.evidence(row['id'], '/audit/sessions/sessions', row['org_id']),
            } for row in failures.order_by('-date_start', '-id').values(
                'id', 'date_start', 'user', 'asset', 'account', 'is_success', 'error_reason', 'org_id',
            )[:SAMPLE_LIMIT]]
            actions.append(self.action_table('session_failure_actions', _('Connection Failures to Review'), failure_rows, stats['failed'], platform_user=True))
            replay_rows = [{
                'time': display_time(row['date_start']), 'user': row['user'], 'asset': row['asset'], 'account': row['account'],
                'issue': recording_labels[row['report_replay']], 'status': _('Awaiting review'),
                'next_step': _('Check recording creation, upload, and storage for the original session.'),
                'evidence': self.evidence(row['id'], '/audit/sessions/sessions', row['org_id']),
            } for row in qs.filter(report_replay__in=['create_failed', 'upload_failed', 'convert_failed', 'unavailable'])
                .order_by('-date_start', '-id').values('id', 'date_start', 'user', 'asset', 'account', 'report_replay', 'org_id')[:SAMPLE_LIMIT]]
            actions.append(self.action_table('recording_actions', _('Recordings to Review'), replay_rows, missing, platform_user=True))
        return source_result(metrics, tables, actions=actions)

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
    def es_rows(store, filters, sort_field, limit=SAMPLE_LIMIT, fields=None):
        response = store.es.search(index=store.query_index, body={
            'query': {'bool': {'filter': filters}}, 'size': limit,
            'sort': [{sort_field: {'order': 'desc'}}],
            **({'_source': fields} if fields else {}),
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
                database_rows = list(db.filter(risk_level__in=risk_levels).order_by('-timestamp').values('id', 'timestamp', 'user', 'asset', 'account', 'input', 'risk_level', 'session', 'org_id')[:SAMPLE_LIMIT])
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
                storage_total, storage_counts = es_counts(store, filters, {
                    str(level): {'term': {'risk_level': int(level)}} for level in levels
                })
                storage_rows = self.es_rows(store, filters + [{'terms': {'risk_level': [int(level) for level in risk_levels]}}], 'timestamp',
                                            fields=['id', 'timestamp', 'user', 'asset', 'account', 'input', 'risk_level', 'session', 'org_id'])
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
            'session': self.evidence(row.get('session'), '/audit/sessions/sessions', row.get('org_id', current_org.id)),
        } for row in sample]
        warnings = []
        tables = [table('command_events', _('Command Decisions Requiring Review'),
                        [('time', _('Time')), ('user', _('Platform User')), ('asset', _('Asset')),
                         ('command', _('Command')), ('action', _('Decision')), ('record', _('Record ID')), ('session', _('Related Session'))],
                        evidence, risk_count)] if available else []
        approval_chapters = ['security', 'remediation']
        if available and set(self.chapters).intersection(approval_chapters):
            approval_issues = []
            try:
                with transaction.atomic():
                    tables.extend(self.command_approval_evidence(sample, approval_issues))
            except Exception:
                logger.exception('Audit report approval evidence unavailable')
                approval_issues.append('unavailable')
            warnings.extend({
                'code': 'command_approval_' + status, 'status': status, 'chapters': approval_chapters,
                'tables': ['command_approvals'],
            } for status in approval_issues)
        actions = []
        if available and 'remediation' in self.chapters:
            action_rows = [{
                'time': item['time'], 'user': item['user'], 'asset': item['asset'], 'account': row.get('account', ''),
                'issue': item['command'], 'status': item['action'],
                'next_step': _('Review the command purpose, matched rule, and approval trail in the original session.'),
                'evidence': item['session'],
            } for row, item in zip(sample, evidence)]
            actions.append(self.action_table('command_review_actions', _('Command Decisions to Review'), action_rows, risk_count, platform_user=True))
        return source_result(metrics if available else [], tables, actions=actions, warnings=warnings,
                             status='available' if complete else ('partial' if available else 'unavailable'), stores=stores)

    def command_approval_evidence(self, commands, issues):
        approval_levels = {str(level) for level in (
            RiskLevelChoices.review_reject, RiskLevelChoices.review_accept, RiskLevelChoices.review_cancel,
        )}
        commands = [row for row in commands if str(row.get('risk_level')) in approval_levels]
        session_ids = [item['session']['id'] for item in (
            {'session': reference(row.get('session'))} for row in commands
        ) if isinstance(item['session'], dict)]
        if not session_ids:
            return []
        if not self.user.has_perm('tickets.view_ticket'):
            issues.append('permission_denied')
            return []
        from tickets.models import ApplyCommandTicket
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
                'ticket': {**self.evidence(ticket.id, '/tickets/tickets/command-confirm', ticket.org_id), 'label': ticket.serial_num or str(ticket.id)[:8]},
                'time': display_time(ticket.date_created), 'command': ticket.apply_run_command,
                'rule': str(snapshot.get('apply_from_cmd_filter_acl') or _('Historical rule name not recorded')),
                'reviewer': ', '.join(step['processor_display'] for step in decisions) or _('No reviewer recorded'),
                'opinion': _('No separate rejection reason was saved; review the ticket discussion'),
                'session': self.evidence(ticket.apply_from_session_id, '/audit/sessions/sessions', ticket.org_id),
            })
        return [table('command_approvals', _('Command Approval Clues from the Same Session'),
                      [('ticket', _('Approval Ticket')), ('time', _('Request Time')), ('command', _('Requested Command')),
                       ('rule', _('Rule at the Time')), ('reviewer', _('Reviewer')), ('opinion', _('Rejection Reason')), ('session', _('Related Session'))],
                      rows, qs.count())]


    def login_queryset(self):
        qs = UserLoginLog.objects.all()
        # Always scope non-root reports, including when enterprise features are off.
        if not current_org.is_root():
            members = current_org.get_members().order_by()
            display_names = members.annotate(report_username=Concat(
                'name', Value('('), 'username', Value(')'), output_field=CharField(),
            )).values('report_username')
            qs = qs.filter(Q(username__in=Subquery(members.values('username'))) |
                           Q(username__in=Subquery(display_names)))
        return qs

    def collect_logins(self):
        from authentication.errors import const
        qs = self.between(self.login_queryset(), 'datetime')
        loopback_q = Q(ip__startswith='127.') | Q(ip='::1') | Q(ip__startswith='::ffff:127.')
        if not self.needs_security_details:
            stats = qs.aggregate(success=Count('id', filter=Q(status=True)),
                                 loopback=Count('id', filter=loopback_q))
            metrics = [metric('login_success', _('Successful Logins'), stats['success'], unit=_('times'))]
            if stats['loopback']:
                metrics.append(metric('loopback_logins', _('Loopback Address Login Records'), stats['loopback'], unit=_('records')))
            return source_result(metrics, actions=[])
        lock_codes = [const.reason_block_user_login, const.reason_block_ip_login, const.reason_block_mfa]
        # Old log versions put the stable code in reason, or use acl_error.
        lock_q = Q(reason_code__in=lock_codes) | Q(reason__in=lock_codes)
        acl_q = Q(reason_code__in=[const.reason_acl_not_allow, 'acl_error']) | Q(reason__in=[const.reason_acl_not_allow, 'acl_error'])
        stats = qs.aggregate(total=Count('id'), success=Count('id', filter=Q(status=True)), failed=Count('id', filter=Q(status=False)),
                             locked=Count('id', filter=Q(status=False) & lock_q), denied=Count('id', filter=Q(status=False) & acl_q),
                             loopback=Count('id', filter=loopback_q))
        metrics = [
            metric('login_success', _('Successful Logins'), stats['success'], unit=_('times')),
            metric('login_failed', _('Failed Logins'), stats['failed'], unit=_('times')),
            metric('login_locked', _('Restricted Login Records'), stats['locked'], unit=_('records')),
            metric('login_denied', _('Login Policy Denials'), stats['denied'], unit=_('records')),
        ]
        failures = qs.filter(status=False)
        rows = [{'time': display_time(row.datetime), 'user': row.username, 'ip': row.ip,
                 'city': row.city or _('Not recorded'), 'reason': str(row.reason_display) or _('Not recorded'),
                 'evidence': self.evidence(row.id, '/audit/audits/login-logs', current_org.id)}
                for row in failures.only('datetime', 'username', 'ip', 'city', 'reason', 'reason_code', 'reason_params').order_by('-datetime')[:SAMPLE_LIMIT]]
        tables = [table('login_failures', _('Recent Failed Logins'), [('time', _('Time')), ('user', _('User')), ('ip', _('Source IP')), ('city', _('City')), ('reason', _('Reason')), ('evidence', _('Original Record'))], rows, stats['failed'])]
        loopback_count = stats['loopback']
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
        city_rows = [{'time': display_time(row['datetime']), 'user': row['username'], 'ip': row['ip'], 'city': row['city'],
                      'evidence': self.evidence(row['id'], '/audit/audits/login-logs', current_org.id)}
                     for row in city_qs.order_by('-datetime').values('id', 'datetime', 'username', 'ip', 'city')[:SAMPLE_LIMIT]]
        tables.append(table('new_city_logins', _('New-City Login Review Clues'), [('time', _('Time')), ('user', _('User')), ('ip', _('Source IP')), ('city', _('City')), ('evidence', _('Original Record'))], city_rows, city_count))
        actions = []
        if 'remediation' in self.chapters:
            actions.append(self.action_table('login_failure_actions', _('Failed Logins to Review'), [{
                'time': row['time'], 'asset': row['ip'], 'account': row['user'],
                'issue': row['reason'], 'status': _('Failed'),
                'next_step': _('Verify the login source and account identity, then review the authentication log.'),
                'evidence': row['evidence'],
            } for row in rows], stats['failed'], asset_label=_('Source IP'), account_label=_('Platform User')))
            actions.append(self.action_table('new_city_actions', _('New-City Logins to Review'), [{
                'time': row['time'], 'asset': row['ip'], 'account': row['user'],
                'issue': row['city'], 'status': _('Awaiting review'),
                'next_step': _('Confirm whether the location change matches travel, proxy use, or expected access.'),
                'evidence': row['evidence'],
            } for row in city_rows], city_count, asset_label=_('Source IP'), account_label=_('Platform User')))
        return source_result(metrics, tables, actions=actions)

    def collect_operations(self):
        es_config = getattr(settings, 'OPERATE_LOG_ELASTICSEARCH_CONFIG', None)
        columns = [('time', _('Time')), ('user', _('User')), ('action', _('Operation')), ('type', _('Resource Type')), ('resource', _('Resource')), ('evidence', _('Original Record'))]
        if es_config:
            from common.plugins.es import ES
            config = copy.deepcopy(es_config)
            config.setdefault('INDEX', 'jumpserver_operate_log')
            # OperateLogStore.__init__ creates indices through pre_use_check().
            # Report generation is a read operation and must not do that.
            store = ES(config, properties={}, keyword_fields={'org_id', 'action'})
            filters = self.es_filters('datetime')
            total, counts = es_counts(store, filters, {'denied': self.es_exact('action', 'reject')})
            denied_filters = filters + [self.es_exact('action', 'reject')]
            denied = counts['denied']
            sample = self.es_rows(store, denied_filters, 'datetime', fields=['id', 'org_id', 'datetime', 'user', 'resource_type', 'resource'])
            rows = [{'time': row.get('datetime', ''), 'user': row.get('user', ''), 'action': _('Rejected'), 'type': row.get('resource_type', ''), 'resource': row.get('resource', ''),
                     'evidence': self.evidence(row.get('id'), '/audit/audits/operate-logs', row.get('org_id', current_org.id))} for row in sample]
        else:
            qs = self.between(OperateLog.objects.all(), 'datetime')
            counts = qs.aggregate(total=Count('id'), denied=Count('id', filter=Q(action='reject')))
            total, denied = counts['total'], counts['denied']
            rejected = qs.filter(action='reject')
            rows = [{'time': display_time(row.datetime), 'user': row.user, 'action': _('Rejected'), 'type': str(row.resource_type_display), 'resource': row.resource,
                     'evidence': self.evidence(row.id, '/audit/audits/operate-logs', row.org_id)}
                    for row in rejected.only('id', 'org_id', 'datetime', 'user', 'resource_type', 'resource').order_by('-datetime')[:SAMPLE_LIMIT]]
        actions = []
        if 'remediation' in self.chapters:
            actions.append(self.action_table('policy_denial_actions', _('Policy Denials to Review'), [{
                'time': row['time'], 'asset': row['resource'], 'account': row['user'],
                'issue': row['type'], 'status': row['action'],
                'next_step': _('Review the denied operation and confirm that the access policy is expected.'),
                'evidence': row['evidence'],
            } for row in rows], denied, asset_label=_('Resource'), account_label=_('Platform User')))
        return source_result([
            metric('operations', _('Platform Operation Count'), total, unit=_('times')),
            metric('policy_rejections', _('Operation Policy Denials'), denied, unit=_('records')),
        ], [table('policy_rejections', _('Policy Denial Details'), columns, rows, denied)], actions=actions)

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
            'session': self.evidence(row['session'], '/audit/sessions/sessions', row['org_id']),
        } for row in failures.order_by('-date_start', '-id').values(
            'id', 'date_start', 'user', 'asset', 'account', 'operate', 'filename', 'session', 'org_id'
        )[:SAMPLE_LIMIT]]
        tables.append(table('failed_files', _('Recent Failed File Operations'),
                            [('time', _('Time')), ('user', _('Platform User')), ('asset', _('Asset')),
                             ('account', _('Asset Account')), ('operation', _('Operation')), ('file', _('File Path')),
                             ('record', _('Record ID')), ('session', _('Related Session'))],
                            rows, stats['failed']))
        actions = []
        if 'remediation' in self.chapters:
            actions.append(self.action_table('file_failure_actions', _('File Operations to Review'), [{
                'time': row['time'], 'user': row['user'], 'asset': row['asset'], 'account': row['account'],
                'issue': f"{row['operation']}: {row['file']}", 'status': _('Failed'),
                'next_step': _('Review the file path, access permissions, and original session before retrying.'),
                'evidence': row['session'],
            } for row in rows], stats['failed'], platform_user=True))
        return source_result([
            metric('file_operations', _('File Operation Count'), stats['total'], unit=_('times')),
            metric('failed_file_operations', _('Failed File Operations'), stats['failed'], unit=_('times')),
            metric('file_failure_rate', _('File Operation Failure Rate'), round(stats['failed'] * 100 / stats['total'], 1) if stats['total'] else None,
                   unit='%', state='value' if stats['total'] else 'not_applicable'),
        ], tables, actions=actions)

    def collect_assets(self):
        from django.db.models import Max

        qs = Asset.objects.all()
        stats = qs.aggregate(total=Count('id'), active=Count('id', filter=Q(is_active=True)), connected=Count('id', filter=Q(connectivity=Connectivity.OK)))
        grouped = qs.order_by().values('platform__name').annotate(count=Count('id')).order_by('-count', 'platform__name')
        failures = [value for value, _label in Connectivity.choices if value not in (Connectivity.OK, Connectivity.UNKNOWN, Connectivity.NA)]
        checks = qs.annotate(report_check=Case(
            When(connectivity=Connectivity.OK, then=Value('success')),
            When(connectivity__in=failures, then=Value('failed')),
            When(connectivity=Connectivity.NA, then=Value('not_applicable')),
            default=Value('unknown'), output_field=CharField(),
        )).order_by().values('report_check').annotate(count=Count('id'), latest_checked=Max('date_verified'))
        checks = {row['report_check']: row for row in checks}
        check_labels = (
            ('success', _('Latest Check Successful')), ('failed', _('Latest Check Failed')),
            ('unknown', _('No Check Result')), ('not_applicable', _('Not Applicable')),
        )
        check_rows = [{
            'status': label, 'count': checks.get(key, {}).get('count', 0),
            'latest_checked': display_time(checks.get(key, {}).get('latest_checked')) or _('Not recorded'),
        } for key, label in check_labels if key != 'not_applicable' or key in checks]
        return source_result([
            metric('assets', _('Current Asset Total'), stats['total'], unit=_('assets')),
            metric('active_assets_inventory', _('Currently Enabled Assets'), stats['active'], unit=_('assets')),
            metric('connected_assets', _('Assets with Latest Check Successful'), stats['connected'], unit=_('assets')),
        ], [table('asset_platforms', _('Current Asset Distribution by Platform'), [('name', _('Platform')), ('count', _('Asset Count'))],
                  [{'name': row['platform__name'] or _('Not recorded'), 'count': row['count']} for row in grouped.iterator()], limit=None),
            table('asset_connectivity', _('Stored Asset Connectivity Results'), [
                ('status', _('Check Result')), ('count', _('Asset Count')), ('latest_checked', _('Most Recent Stored Check')),
            ], check_rows)])

    def collect_accounts(self):
        from django.db.models import Max

        qs = Account.objects.all()
        stats = qs.aggregate(total=Count('id'), active=Count('id', filter=Q(is_active=True)), connected=Count('id', filter=Q(connectivity=Connectivity.OK)))
        grouped = qs.order_by().values('asset__name').annotate(count=Count('id')).order_by('-count', 'asset__name')
        failures = [value for value, _label in Connectivity.choices if value not in (Connectivity.OK, Connectivity.UNKNOWN, Connectivity.NA)]
        checks = qs.annotate(report_check=Case(
            When(connectivity=Connectivity.OK, then=Value('success')),
            When(connectivity__in=failures, then=Value('failed')),
            When(connectivity=Connectivity.NA, then=Value('not_applicable')),
            default=Value('unknown'), output_field=CharField(),
        )).order_by().values('report_check').annotate(count=Count('id'), latest_checked=Max('date_verified'))
        checks = {row['report_check']: row for row in checks}
        check_labels = (
            ('success', _('Latest Check Successful')), ('failed', _('Latest Check Failed')),
            ('unknown', _('No Check Result')), ('not_applicable', _('Not Applicable')),
        )
        check_rows = [{
            'status': label, 'count': checks.get(key, {}).get('count', 0),
            'latest_checked': display_time(checks.get(key, {}).get('latest_checked')) or _('Not recorded'),
        } for key, label in check_labels if key != 'not_applicable' or key in checks]
        return source_result([
            metric('accounts', _('Current Managed Accounts'), stats['total'], unit=_('accounts')),
            metric('active_accounts', _('Currently Enabled Accounts'), stats['active'], unit=_('accounts')),
            metric('connected_accounts', _('Managed Accounts with Latest Check Successful'), stats['connected'], unit=_('accounts')),
        ], [table('accounts_by_asset', _('Asset Account Count Ranking'), [('name', _('Asset')), ('count', _('Account Count'))],
                  [{'name': row['asset__name'] or _('Not recorded'), 'count': row['count']} for row in grouped.iterator()], limit=None),
            table('account_connectivity', _('Stored Managed Account Connectivity Results'), [
                ('status', _('Check Result')), ('count', _('Account Count')), ('latest_checked', _('Most Recent Stored Check')),
            ], check_rows)])

    @staticmethod
    def risk_next_step(risk, status):
        if status == ConfirmOrIgnore.confirmed:
            return _('Review the confirmed finding and verify the current account state.')
        if status == ConfirmOrIgnore.ignored:
            return _('Review whether the reason for ignoring this risk still applies.')
        steps = {
            RiskChoice.weak_password: _('Replace the weak password with a strong unique password, then verify account access.'),
            RiskChoice.leaked_password: _('Rotate the potentially exposed credential, review recent access, and verify dependent services.'),
            RiskChoice.repeated_password: _('Assign a unique credential to each affected account, synchronize dependent services, and verify access.'),
            RiskChoice.password_expired: _('Renew the expired credential and verify dependent tasks and account access.'),
            RiskChoice.long_time_password: _('Rotate the credential according to the rotation policy and verify dependent services.'),
            RiskChoice.new_found: _('Confirm the account owner and purpose, then manage approved accounts or disable unauthorized accounts.'),
            RiskChoice.account_deleted: _('Confirm whether deletion was approved, then reconcile the managed account inventory.'),
            RiskChoice.long_time_no_login: _('Confirm whether the account is still needed, then disable unused accounts after approval.'),
            RiskChoice.group_changed: _('Compare group membership changes with approved access, and remove unapproved privileges.'),
            RiskChoice.sudo_changed: _('Compare sudo permission changes with approved access, and remove unapproved privileges.'),
            RiskChoice.authorized_keys_changed: _('Compare authorized keys with approved keys, and remove unapproved keys.'),
        }
        if risk in steps:
            return steps[risk]
        return _('Compare the detected change with approved access and confirm the handling result.')

    def collect_account_risks(self):
        from django.db.models.functions import Concat

        credential_risks = {
            RiskChoice.weak_password, RiskChoice.leaked_password, RiskChoice.repeated_password,
            RiskChoice.password_expired, RiskChoice.long_time_password,
        }
        managed = Account.objects.filter(
            asset_id=OuterRef('asset_id'), username=OuterRef('username'), org_id=OuterRef('org_id'),
        )
        qs = AccountRisk.objects.annotate(
            report_managed=Exists(managed),
            report_account_key=Concat(Cast('asset_id', CharField()), Value(':'), 'username'),
            report_status_order=Case(
                When(Q(status=ConfirmOrIgnore.pending) | Q(status=''), then=Value(0)),
                When(status=ConfirmOrIgnore.confirmed, then=Value(1)),
                When(status=ConfirmOrIgnore.ignored, then=Value(2)),
                default=Value(3), output_field=IntegerField(),
            ),
            report_risk_order=Case(
                When(risk__in=credential_risks, then=Value(0)),
                default=Value(1), output_field=IntegerField(),
            ),
        )
        pending = qs.filter(Q(status=ConfirmOrIgnore.pending) | Q(status=''))
        stats = qs.aggregate(
            total=Count('id'), confirmed=Count('id', filter=Q(status=ConfirmOrIgnore.confirmed)),
            ignored=Count('id', filter=Q(status=ConfirmOrIgnore.ignored)),
        )
        impact = pending.aggregate(
            records=Count('id'), assets=Count('asset_id', distinct=True),
            accounts=Count('report_account_key', distinct=True),
            managed_accounts=Count('report_account_key', distinct=True, filter=Q(report_managed=True)),
            unmanaged_accounts=Count('report_account_key', distinct=True, filter=Q(report_managed=False)),
        )
        metrics = [
            metric('risk_total', _('Current Risk Records'), stats['total'], unit=_('records')),
            metric('risk_pending', _('Pending Risk Records'), impact['records'], unit=_('records')),
            metric('risk_confirmed', _('Confirmed Risk Records'), stats['confirmed'], unit=_('records')),
            metric('risk_ignored', _('Ignored Risk Records'), stats['ignored'], unit=_('records')),
            metric('risk_assets', _('Assets with Pending Risks'), impact['assets'], unit=_('assets')),
            metric('risk_accounts', _('Accounts Identified in Pending Risks'), impact['accounts'], unit=_('accounts')),
            metric('risk_managed_accounts', _('Risk Accounts Matched to Managed Accounts'), impact['managed_accounts'], unit=_('accounts')),
            metric('risk_unmanaged_accounts', _('Risk Accounts Not Matched to Managed Accounts'), impact['unmanaged_accounts'], unit=_('accounts')),
        ]
        labels = dict(RiskChoice.choices)
        status_labels = dict(ConfirmOrIgnore.choices)
        status_labels[ConfirmOrIgnore.pending] = _('Awaiting review')
        groups = list(pending.order_by().values('risk').annotate(
            count=Count('id'), account_count=Count('report_account_key', distinct=True), asset_count=Count('asset_id', distinct=True),
        ).order_by('-count', 'risk'))
        tables = [table('risk_types', _('Pending Risks by Type'), [('name', _('Risk')), ('count', _('Risk Count'))],
                        [{'name': str(labels.get(row['risk'], row['risk'])), 'count': row['count']} for row in groups])]
        # Read only identification and status fields, never details or account credentials.
        rows = []
        for row in qs.order_by('report_status_order', 'report_risk_order', '-date_updated', '-id').values(
            'id', 'org_id', 'asset__name', 'asset__address', 'username', 'risk', 'status', 'date_updated',
        )[:SAMPLE_LIMIT]:
            evidence = reference(row['id'], org_id=row['org_id'])
            evidence.update(path='/pam/security/check', query={'tab': 'AccountRisks', 'id': evidence['id']})
            rows.append({
                'asset': row['asset__name'], 'address': row['asset__address'], 'account': row['username'],
                'risk': str(labels.get(row['risk'], row['risk'])),
                'status': str(status_labels.get(row['status'], row['status'] or _('Awaiting review'))),
                'updated': display_time(row['date_updated']),
                'next_step': self.risk_next_step(row['risk'], row['status']), 'evidence': evidence,
            })
        tables.append(table('account_risks', _('Current Account Risk Details'), [
            ('asset', _('Asset')), ('address', _('Address')), ('account', _('Account')),
            ('risk', _('Risk')), ('status', _('Status')), ('updated', _('Updated')),
            ('next_step', _('Next Step')), ('evidence', _('Original Record')),
        ], rows, stats['total']))
        actions = []
        if 'remediation' in self.chapters:
            action_rows = [{
                'risk': str(labels.get(row['risk'], row['risk'])), 'record_count': row['count'],
                'account_count': row['account_count'], 'asset_count': row['asset_count'],
                'next_step': self.risk_next_step(row['risk'], ConfirmOrIgnore.pending),
                'evidence': {
                    'kind': 'account_risk_group', 'path': '/pam/security/check', 'org_id': str(current_org.id),
                    'query': {'tab': 'AccountRisks', 'risk': str(row['risk']), 'status': '0'},
                    'label': _('Review risks'),
                },
            } for row in sorted(groups, key=lambda row: (row['risk'] not in credential_risks, -row['count'], row['risk']))]
            actions.append(table('account_risk_actions', _('Account Risks to Review'), [
                ('risk', _('Risk')), ('record_count', _('Risk Records')),
                ('account_count', _('Affected Accounts')), ('asset_count', _('Affected Assets')),
                ('next_step', _('Next Step')), ('evidence', _('Risk List')),
            ], action_rows, limit=len(RiskChoice.choices)))
        return source_result(metrics, tables, actions=actions)

    def collect_automation(self):
        types = [AutomationTypes.push_account, AutomationTypes.check_account, AutomationTypes.backup_account,
                 AutomationTypes.gather_accounts, AutomationTypes.change_secret, AutomationTypes.verify_account]
        qs = self.between(AutomationExecution.objects.filter(type__in=types), 'date_start')
        stats = qs.aggregate(total=Count('id'), success=Count('id', filter=Q(status=Status.success)),
                             failed=Count('id', filter=Q(status__in=[Status.failed, Status.error])),
                             canceled=Count('id', filter=Q(status=Status.canceled)),
                             pending=Count('id', filter=Q(status__in=[Status.ready, Status.pending, Status.running])))
        metrics = [
            metric('automation_executions', _('Account Task Executions'), stats['total'], unit=_('times')),
            metric('automation_success', _('Successful Executions'), stats['success'], unit=_('times')),
            metric('automation_failed', _('Failed or Errored Executions'), stats['failed'], unit=_('times')),
            metric('automation_pending', _('Incomplete Executions'), stats['pending'], unit=_('times')),
            metric('automation_canceled', _('Canceled'), stats['canceled'], unit=_('times')),
        ]
        labels = dict(AutomationTypes.choices)
        labels[AutomationTypes.change_secret] = _('Account change secret')
        grouped = qs.order_by().values('type', 'status').annotate(count=Count('id')).order_by('type', 'status')
        status_labels = dict(Status.choices)
        rows = [{'name': str(labels.get(row['type'], row['type'])), 'status': str(status_labels.get(row['status'], row['status'])), 'count': row['count']} for row in grouped]
        tables = [table('automation_results', _('Account Task Types and Results'), [('name', _('Task Type')), ('status', _('Result')), ('count', _('Execution Count'))], rows, limit=100)]
        failures = qs.filter(status__in=[Status.failed, Status.error])
        # Never deserialize encrypted execution snapshots: those contain secrets.
        execution_paths = {
            AutomationTypes.change_secret: '/pam/security/account-change-secret/executions',
            AutomationTypes.backup_account: '/pam/automations/account-backup/executions',
            AutomationTypes.push_account: '/pam/automations/account-push/executions',
            AutomationTypes.gather_accounts: '/pam/automations/account-discovery/executions',
            AutomationTypes.check_account: '/pam/security/check/executions',
        }
        rows = [{
            'time': display_time(row['date_start']),
            'id': self.evidence(row['id'], execution_paths[row['type']], row['org_id']) if row['type'] in execution_paths else str(row['id']),
            'name': str(labels.get(row['type'], row['type'])),
            'status': str(status_labels.get(row['status'], row['status'])),
        } for row in failures.order_by('-date_start').values('id', 'type', 'status', 'date_start', 'org_id')[:SAMPLE_LIMIT]]
        tables.append(table('failed_automations', _('Recent Failed Account Tasks'), [('time', _('Start Time')), ('name', _('Task Type')), ('status', _('Result')), ('id', _('Original Execution Record'))], rows, stats['failed']))
        metrics.append(metric('automation_failure_rate', _('Task Failure or Error Rate'),
                              round(stats['failed'] * 100 / stats['total'], 1) if stats['total'] else None,
                              unit='%', state='value' if stats['total'] else 'not_applicable'))
        warnings = []
        actions = []
        if 'remediation' in self.chapters:
            actions.append(table('automation_actions', _('Account Tasks to Review'), [
                ('time', _('Time')), ('issue', _('Task Type')), ('status', _('Status')),
                ('next_step', _('Next Step')), ('evidence', _('Original Record')),
            ], [{
                'time': row['time'], 'issue': row['name'], 'status': row['status'],
                'next_step': _('Review the execution log and affected targets, correct the cause, then retry.'),
                'evidence': row['id'],
            } for row in rows], stats['failed']))
        detail_chapters = ['account', 'remediation']
        if set(self.chapters).intersection(detail_chapters):
            detail_metrics, detail_tables, detail_issues, detail_actions = [], [], [], []
            try:
                with transaction.atomic():
                    self.change_secret_evidence(qs, detail_metrics, detail_tables, detail_issues, detail_actions)
                metrics.extend(detail_metrics)
                tables.extend(detail_tables)
                actions.extend(detail_actions)
            except Exception:
                logger.exception('Audit report change-secret evidence unavailable')
                detail_issues.append('unavailable')
            warnings.extend({
                'code': 'password_change_details_' + status, 'status': status, 'chapters': detail_chapters,
                'tables': ['change_secret_reasons', 'change_secret_followup', 'change_secret_progress',
                           'change_secret_followup_actions', 'change_secret_progress_actions'],
            } for status in detail_issues)
        return source_result(metrics, tables, actions=actions, warnings=warnings)

    @staticmethod
    def change_secret_progress(row):
        if row['ignore_fail']:
            return _('Ignored'), _('Review whether the reason for ignoring this failure still applies.')
        if row['later_success']:
            return _('Later password change succeeded'), _('Confirm that the newer credential is synchronized and access works.')
        if row['verification_status'] == 'pending':
            return _('Credential verification in progress'), _('Wait for verification to finish before deciding whether to synchronize the credential.')
        if row['verification_status'] == 'success':
            return _('Candidate credential verified'), _('Review and synchronize the verified candidate credential; verification alone does not confirm recovery.')
        if row['verification_status'] == 'failed':
            return _('Credential verification failed'), _('Review the verification result and original execution before retrying.')
        return _('Awaiting review'), _('Verify the candidate credential and synchronize it only after confirming that access works.')

    def change_secret_evidence(self, executions, metrics, tables, issues, actions):
        executions = executions.filter(type=AutomationTypes.change_secret)
        if not executions.exists():
            return
        if not self.user.has_perm('accounts.view_changesecretrecord'):
            issues.append('permission_denied')
            return
        records = ChangeSecretRecord.objects.filter(execution_id__in=Subquery(executions.values('id')))
        failures = records.filter(status__in=['failed', 'unverified'])
        if not failures.exists():
            return
        later = ChangeSecretRecord.objects.filter(
            account_id=OuterRef('account_id'), asset_id=OuterRef('asset_id'),
            execution__org_id=OuterRef('execution__org_id'), status='success',
            date_finished__gt=OuterRef('date_finished'), date_finished__lte=self.generated_at,
        )
        failures = failures.annotate(later_success=Exists(later))
        outstanding = failures.filter(ignore_fail=False, later_success=False)
        progressed = failures.filter(Q(ignore_fail=True) | Q(later_success=True))
        impact = outstanding.aggregate(total=Count('id'), assets=Count('asset_id', distinct=True), accounts=Count('account_id', distinct=True))
        metrics.extend([
            metric('change_secret_affected_assets', _('Assets with Password Changes Requiring Review'), impact['assets'], unit=_('assets')),
            metric('change_secret_affected_accounts', _('Accounts with Password Changes Requiring Review'), impact['accounts'], unit=_('accounts')),
        ])
        labels = error_category_labels()
        categorized = outstanding.annotate(report_reason=error_category_expression())
        groups = categorized.order_by().values('report_reason').annotate(count=Count('id')).order_by('-count')
        tables.append(table('change_secret_reasons', _('Top 5 Password-Change Error Clues'), [('name', _('Error Clue Category')), ('count', _('Account Record Count'))],
                            [{'name': labels[row['report_reason']], 'count': row['count']} for row in groups[:5]],
                            total=groups.count(), limit=5))
        for key, records, title, total, has_progress in (
            ('change_secret_followup', categorized, _('Password-Change Accounts Requiring Review'), impact['total'], False),
            ('change_secret_progress', progressed.annotate(report_reason=error_category_expression()),
             _('Password Changes with Subsequent Progress'), progressed.count(), True),
        ):
            rows = []
            for row in records.order_by('-date_finished', '-id').values(
                'date_finished', 'asset__name', 'account__username', 'report_reason', 'later_success',
                'execution_id', 'execution__org_id', 'verification_status', 'date_verified', 'ignore_fail',
            )[:SAMPLE_LIMIT]:
                followup, next_step = self.change_secret_progress(row)
                rows.append({
                    'time': display_time(row['date_finished']), 'asset': row['asset__name'] or _('Asset deleted'),
                    'account': row['account__username'] or _('Account deleted'), 'reason': labels[row['report_reason']],
                    'followup': followup, 'verified': display_time(row['date_verified']) or _('Not recorded'),
                    'next_step': next_step,
                    'execution': self.evidence(row['execution_id'], '/pam/security/account-change-secret/executions', row['execution__org_id']),
                })
            tables.append(table(key, title,
                                [('time', _('Record Time')), ('asset', _('Asset')), ('account', _('Account')),
                                 ('reason', _('Error Clue')), ('followup', _('Handling Progress')), ('verified', _('Verification Time')),
                                 ('next_step', _('Next Step')), ('execution', _('Execution Record'))], rows, total))
            if 'remediation' in self.chapters and total:
                action = self.action_table(key + '_actions', title, [{
                    'time': row['time'], 'asset': row['asset'], 'account': row['account'], 'issue': row['reason'],
                    'status': row['followup'], 'next_step': row['next_step'], 'evidence': row['execution'],
                } for row in rows], total)
                action['has_progress'] = has_progress
                actions.append(action)


    def collect_password_changes(self):
        qs = PasswordChangeLog.objects.all()
        if not current_org.is_root():
            from audits.models import user_display_expression
            names = current_org.get_members().annotate(display=user_display_expression()).values('display')
            qs = qs.filter(user__in=Subquery(names))
        qs = self.between(qs, 'datetime')
        count = qs.count()
        rows = [{'time': display_time(row['datetime']), 'user': row['user'], 'operator': row['change_by'],
                 'ip': row['remote_addr'] or _('Not recorded'), 'record': str(row['id'])}
                for row in qs.order_by('-datetime').values('id', 'datetime', 'user', 'change_by', 'remote_addr')[:SAMPLE_LIMIT]]
        return source_result([
            metric('platform_password_changes', _('Platform User Password Changes'), count, unit=_('times')),
        ], [table('platform_password_changes', _('Recent Platform User Password Changes'), [('time', _('Time')), ('user', _('User')), ('operator', _('Operator')),
                   ('ip', _('Source IP')), ('record', _('Record ID'))], rows, count)])

    def conclusions(self):
        values = {}
        for key, data in self.data.items():
            if self.sources[key]['status'] == 'available':
                values.update({item['key']: item['value'] for item in data['metrics']})
        conclusions = []
        if 'risk_pending' in values:
            if values['risk_pending']:
                conclusions.append(_('Currently, %(pending)s pending account risk records involve %(accounts)s distinct accounts on %(assets)s assets. Review the affected accounts by risk type.') % {
                    'pending': values['risk_pending'], 'accounts': values['risk_accounts'], 'assets': values['risk_assets']})
            elif values.get('risk_total'):
                conclusions.append(_('There are currently no pending account risk records.'))
            else:
                conclusions.append(_('No account risk records are currently available.'))
        if 'activity' in self.topic_chapters and 'sessions' in values:
            conclusions.append(_('%(sessions)s asset sessions were recorded: %(success)s connections succeeded and %(failed)s failed, involving %(users)s users and %(assets)s assets.') % {
                'sessions': values['sessions'], 'success': values['sessions'] - values['failed_sessions'],
                'failed': values['failed_sessions'], 'users': values['active_users'], 'assets': values['active_assets']})
        if 'activity' in self.topic_chapters or 'remediation' in self.topic_chapters:
            if values.get('failed_file_operations'):
                conclusions.append(_('%(failed)s of %(total)s file operations failed (%(rate)s%%). Review the affected assets, accounts, file paths, and original sessions.') % {
                    'failed': values['failed_file_operations'], 'total': values['file_operations'], 'rate': values['file_failure_rate']})
            if values.get('failed_sessions'):
                conclusions.append(_('Review failed connections using the affected assets, accounts, and recorded reasons.'))
            if values.get('replay_attention'):
                conclusions.append(_('%(count)s completed successful sessions require recording review. Check recording creation, upload, and storage.') % {'count': values['replay_attention']})
        review_security = 'security' in self.topic_chapters or 'remediation' in self.topic_chapters
        command_risk = sum(values.get('command_' + str(level), 0) for level in [4, 5, 6])
        if review_security and command_risk:
            conclusions.append(_('%(count)s alerted or rejected commands were recorded. Review their purpose and approval basis in the session context.') % {'count': command_risk})
        if review_security and values.get('login_failed'):
            conclusions.append(_('%(count)s platform logins failed. Review the affected users, source addresses, and recorded reasons.') % {'count': values['login_failed']})
        if review_security and (values.get('login_locked', 0) or values.get('login_denied', 0)):
            conclusions.append(_('Restricted logins or policy denials were recorded. Verify that the source, user identity, and access policy are expected.'))
        if review_security and values.get('new_city_logins', 0):
            conclusions.append(_('%(count)s new-city login records require review of user identity and access location.') % {'count': values['new_city_logins']})
        if review_security and values.get('policy_rejections', 0):
            conclusions.append(_('The operation log contains %(count)s policy denials. Check the denied resources and policies in the audit details.') % {'count': values['policy_rejections']})
        event_keys = ('login_failed', 'login_locked', 'login_denied', 'new_city_logins', 'policy_rejections', 'command_4', 'command_5', 'command_6')
        security_available = all(
            not self.source_has_issues(key, 'security')
            for key in self.sources_for_chapter('security') if key in self.sources
        )
        if 'security' in self.topic_chapters and security_available and any(key in values for key in event_keys) and not any(values.get(key) for key in event_keys):
            conclusions.append(_('No listed security events were found in the available records for this period.'))
        if ('account' in self.topic_chapters or 'remediation' in self.topic_chapters) and 'automation_executions' in values:
            conclusions.append(_('%(total)s account tasks were executed: %(success)s succeeded, %(failed)s failed or errored, and %(pending)s remain incomplete.') % {
                'total': values['automation_executions'], 'success': values['automation_success'],
                'failed': values['automation_failed'], 'pending': values['automation_pending']})
            if values.get('automation_canceled'):
                conclusions.append(_('%(count)s account task executions were canceled.') % {'count': values['automation_canceled']})
            if values.get('automation_failed'):
                conclusions.append(_('Review failed task logs and affected accounts; prioritize unresolved items before records with subsequent progress.'))
        if 'account' in self.topic_chapters and values.get('platform_password_changes', 0):
            conclusions.append(_('%(count)s platform user password changes were recorded. Review the operators and change rationale as needed.') % {'count': values['platform_password_changes']})
        if 'inventory' in self.topic_chapters and 'activity' not in self.topic_chapters:
            if 'assets' in values:
                conclusions.append(_('There are currently %(total)s assets, of which %(active)s are enabled.') % {
                    'total': values['assets'], 'active': values['active_assets_inventory']})
            if 'accounts' in values:
                conclusions.append(_('There are currently %(total)s managed account records, of which %(active)s are enabled.') % {
                    'total': values['accounts'], 'active': values['active_accounts']})
        if values.get('loopback_logins'):
            conclusions.append(_('%(count)s platform login records use loopback source addresses. Confirm whether these are local accesses or proxy-forwarded requests.') % {'count': values['loopback_logins']})
        if 'remediation' in self.topic_chapters and not conclusions and any(source['status'] == 'available' for source in self.sources.values()):
            review_items = [item for data in self.data.values() for item in data.get('actions', []) if item['total'] and not item.get('has_progress')]
            if review_items:
                conclusions.extend(f"{item['title']}: {item['total']}" for item in review_items)
        return conclusions

    def source_has_issues(self, key, chapter=None):
        source = self.sources[key]
        return source['status'] != 'available' or any(
            chapter is None or chapter in warning['chapters']
            for warning in source.get('warnings', [])
        )

    def overview_metrics(self, topic_chapters):
        chapter_metrics = {
            'activity': {'sessions', 'active_users', 'active_assets', 'failed_sessions', 'replay_attention', 'commands', 'file_operations', 'failed_file_operations', 'operations', 'login_success'},
            'security': {'login_failed', 'command_5', 'command_4', 'command_6', 'login_locked', 'login_denied', 'new_city_logins', 'policy_rejections'},
            'inventory': {'assets', 'accounts', 'active_assets_inventory', 'active_accounts', 'connected_assets', 'connected_accounts'},
            'account': {'automation_executions', 'automation_failed', 'automation_success', 'automation_pending', 'platform_password_changes'},
            'account_health': {'risk_total', 'risk_pending', 'risk_confirmed', 'risk_ignored', 'risk_assets', 'risk_accounts', 'risk_managed_accounts', 'risk_unmanaged_accounts'},
            'remediation': {'risk_pending', 'risk_assets', 'risk_accounts', 'failed_sessions', 'replay_attention', 'failed_file_operations', 'automation_failed', 'login_failed', 'command_4', 'command_5', 'command_6', 'policy_rejections', 'new_city_logins'},
        }
        allowed = set().union(*(chapter_metrics[key] for key in topic_chapters))
        metrics = {item['key']: item for data in self.data.values() for item in data['metrics']}
        primary = {
            'audit': ('risk_pending', 'risk_accounts', 'risk_assets', 'sessions', 'active_users', 'active_assets'),
            'activity': ('sessions', 'active_users', 'active_assets', 'commands', 'file_operations', 'operations'),
            'security': ('login_failed', 'command_4', 'command_5', 'command_6', 'login_denied', 'policy_rejections'),
            'inventory': ('assets', 'accounts', 'risk_pending', 'risk_accounts', 'risk_managed_accounts', 'risk_unmanaged_accounts'),
            'account': ('automation_executions', 'automation_success', 'automation_failed', 'automation_pending', 'risk_pending', 'risk_accounts'),
        }[self.theme]
        attention = ('risk_pending', 'risk_accounts', 'risk_assets', 'replay_attention', 'failed_sessions', 'failed_file_operations', 'automation_failed', 'login_failed', 'command_4', 'command_5', 'command_6', 'login_denied', 'policy_rejections', 'new_city_logins')
        # Nonzero issues stay visible even if the theme has many volume metrics.
        ordered = list(dict.fromkeys(
            [key for key in attention if metrics.get(key, {}).get('value')] + list(primary)
        ))
        fallback = ('sessions', 'active_users', 'active_assets', 'assets', 'accounts', 'automation_executions', 'automation_success', 'automation_failed', 'automation_pending', 'risk_pending', 'risk_accounts', 'risk_assets', 'commands', 'file_operations', 'operations', 'login_success', 'login_failed')
        selected = [key for key in ordered if key in allowed and key in metrics]
        if len(selected) < 6:
            for key in fallback:
                if key in allowed and key in metrics and key not in selected:
                    selected.append(key)
                    if len(selected) >= 6:
                        break
        return [copy.deepcopy(metrics[key]) for key in selected]

    def build(self):
        topic_chapters = [chapter for chapter in self.chapters if chapter in CHAPTER_SOURCES]
        # An overview-only report still needs the selected theme's data. A custom
        # subset of substantive chapters never silently collects other chapters.
        if not topic_chapters and any(chapter in self.chapters for chapter in ('overview', 'conclusion')):
            topic_chapters = [chapter for chapter in THEME_CHAPTERS[self.theme] if chapter in CHAPTER_SOURCES]
        self.topic_chapters = topic_chapters
        for chapter in topic_chapters:
            for key in self.sources_for_chapter(chapter):
                self.collect(key)
        conclusions = self.conclusions()
        titles = {'overview': _('Key Overview'), 'activity': _('Operations Activity Analysis'),
                  'security': _('Security Event Analysis'), 'inventory': _('Asset and Account Overview'),
                  'account': _('Account Operations Analysis'), 'account_health': _('Account Health'),
                  'remediation': _('Remediation Checklist'),
                  'conclusion': _('Management Summary and Recommendations')}
        sections = []
        for chapter in self.chapters:
            section = {'key': chapter, 'title': titles[chapter], 'description': '',
                       'status': 'available', 'metrics': [], 'tables': [], 'notes': [], 'has_issues': False}
            if chapter in CHAPTER_SOURCES:
                sources = self.sources_for_chapter(chapter)
                for key in sources:
                    if chapter == 'remediation':
                        section['tables'].extend(copy.deepcopy([item for item in self.data[key].get('actions', []) if item['total']]))
                    else:
                        section['metrics'].extend(copy.deepcopy(self.data[key]['metrics']))
                        section['tables'].extend(copy.deepcopy(self.data[key]['tables']))
                    section['has_issues'] = section['has_issues'] or self.source_has_issues(key, chapter)
                statuses = [self.sources[key]['status'] for key in sources]
                section['status'] = 'available' if all(status == 'available' for status in statuses) else ('partial' if any(status in ('available', 'partial') for status in statuses) else 'unavailable')
                if chapter == 'remediation':
                    section['tables'].sort(key=lambda item: bool(item.get('has_progress')))
                # Keep operational and risk views focused, while using the same
                # collected source data and queries in an integrated report.
                if chapter == 'activity':
                    section['tables'] = [item for item in section['tables'] if item['key'] not in ('command_events', 'command_approvals', 'login_failures', 'new_city_logins', 'policy_rejections')]
                    section['metrics'] = [item for item in section['metrics'] if not item['key'].startswith('command_') and item['key'] not in ('login_failed', 'login_locked', 'login_denied', 'new_city_logins', 'policy_rejections')]
                if chapter == 'security':
                    section['metrics'] = [item for item in section['metrics'] if item['key'] not in ('operations', 'commands', 'login_success')]
            elif chapter == 'overview':
                section['metrics'] = self.overview_metrics(topic_chapters)
                section['has_issues'] = any(source['has_issues'] for source in self.sources.values())
                if section['has_issues']:
                    section['status'] = 'partial'
            elif chapter == 'conclusion':
                section['has_issues'] = any(source['has_issues'] for source in self.sources.values())
            if section['has_issues'] and section['status'] == 'available':
                section['status'] = 'partial'
            sections.append(section)
        sources = list(self.sources.values())
        partial = any(source['has_issues'] for source in sources)
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
