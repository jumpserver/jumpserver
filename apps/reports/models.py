import uuid
from decimal import Decimal
from urllib.parse import urlencode

from celery import current_task, shared_task
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.const.choices import Status, Trigger
from common.db.fields import JSONManyToManyField
from common.db.models import JMSBaseModel
from common.utils import get_logger
from notifications.backends import BACKEND
from notifications.models import UserMsgSubscription
from ops.celery.decorator import after_app_ready_start
from ops.celery.utils import create_or_update_celery_periodic_tasks
from ops.mixin import PeriodTaskModelMixin
from orgs.mixins.models import JMSOrgBaseModel, OrgModelMixin
from orgs.utils import tmp_to_org
from users.models import User

from .mixins import CREATABLE_REPORT_TYPES, REPORT_FILTER_FIELDS, build_report_content, resolve_range
from .views import charts_map

logger = get_logger(__name__)


class Report(PeriodTaskModelMixin, JMSOrgBaseModel):
    tp = models.CharField(max_length=64, verbose_name=_('Type'))
    is_builtin = models.BooleanField(default=False, verbose_name=_('Is builtin'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    range_days = models.PositiveIntegerField(default=7, verbose_name=_('Range days'))
    filters = models.JSONField(default=dict, verbose_name=_('Filters'))
    recipients = JSONManyToManyField('users.User', default=dict, verbose_name=_('Recipients'))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('Report')
        ordering = ['-date_created']

    def get_register_task(self):
        return f'report_send_{str(self.id)[:8]}', execute_report.name, (str(self.id), Trigger.timing), {}

    def to_attr_json(self):
        recipients = getattr(self, 'recipients', None)
        recipient_ids = recipients.value if hasattr(recipients, 'value') else []
        return {
            'name': self.name,
            'tp': self.tp,
            'range_days': self.range_days,
            'filters': self.filters,
            'recipients': recipient_ids,
            'org_id': self.org_id,
        }

    def execute(self, trigger=Trigger.manual):
        try:
            execution_id = current_task.request.id
        except AttributeError:
            execution_id = str(uuid.uuid4())
        return ReportExecution.objects.create(
            id=execution_id,
            report=self,
            trigger=trigger,
            snapshot=self.to_attr_json(),
            org_id=self.org_id,
        )


class ReportExecution(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    report = models.ForeignKey(Report, related_name='executions', on_delete=models.CASCADE, null=True)
    status = models.CharField(max_length=16, default=Status.pending, choices=Status.choices)
    date_created = models.DateTimeField(auto_now_add=True)
    date_start = models.DateTimeField(null=True, db_index=True)
    date_finished = models.DateTimeField(null=True)
    duration = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    trigger = models.CharField(max_length=128, default=Trigger.manual, choices=Trigger.choices)
    snapshot = models.JSONField(default=dict)
    summary = models.JSONField(default=dict)

    class Meta:
        ordering = ('org_id', '-date_start')


class ReportSendRecord(JMSBaseModel, OrgModelMixin):
    execution = models.ForeignKey(ReportExecution, related_name='send_records', on_delete=models.CASCADE)
    backend = models.CharField(max_length=32, blank=True, default='')
    receiver = models.CharField(max_length=128, blank=True, default='')
    report_url = models.TextField(blank=True, default='')
    is_success = models.BooleanField(default=True)
    error = models.TextField(blank=True, default='')
    detail = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-date_created']


def validate_report_payload(tp, filters):
    if tp not in CREATABLE_REPORT_TYPES:
        raise ValueError(f'Unsupported report type: {tp}')
    invalid_keys = set((filters or {}).keys()) - set(REPORT_FILTER_FIELDS.get(tp, []))
    if invalid_keys:
        raise ValueError(f'Invalid filters: {", ".join(sorted(invalid_keys))}')


def build_report_url(report):
    chart_info = charts_map.get(report.tp) or {}
    path = chart_info.get('path')
    if not path:
        return report.name, ''
    url = getattr(settings, 'SITE_URL', '').rstrip('/') + path
    range_info = resolve_range(
        start=(report.filters or {}).get('start'),
        end=(report.filters or {}).get('end'),
        preset=(report.filters or {}).get('range_preset', ''),
        days=report.range_days,
    )
    params = {
        'start': range_info['start'].strftime('%Y-%m-%d'),
        'end': range_info['end'].strftime('%Y-%m-%d'),
        'oid': report.org_id,
        'report_id': str(report.id),
    }
    user_value = (report.filters or {}).get('user_id')
    if user_value:
        params['user_id'] = user_value
    for key in ('asset_id', 'account'):
        value = (report.filters or {}).get(key)
        if value:
            params[key] = value
    separator = '&' if '?' in url else '?'
    return report.name, url + separator + urlencode(params)


class ReportLinkMsg:
    def __init__(self, title, report_url):
        self.title = title
        self.report_url = report_url

    def get_backend_msg_mapper(self, receive_backends):
        payload = {
            'subject': str(_('Periodic report')),
            'message': self.report_url,
            'html_message': f'<p>{self.title}</p><p>{self.report_url}</p>',
        }
        return {backend: payload for backend in (receive_backends or [])}


def finish_execution(execution, status, summary):
    now = timezone.now()
    duration = 0
    if execution.date_start:
        duration = (now - execution.date_start).total_seconds()
    execution.status = status
    execution.summary = summary
    execution.date_finished = now
    execution.duration = Decimal(str(round(duration, 2)))
    execution.save(update_fields=['status', 'summary', 'date_finished', 'duration'])


@shared_task
def execute_report(report_id, trigger=Trigger.manual):
    report = Report.objects.filter(id=report_id).first()
    if not report:
        return
    if trigger == Trigger.timing and (not report.is_periodic or not report.is_active):
        return
    execution = report.execute(trigger=trigger)
    execution.status = Status.running
    execution.date_start = timezone.now()
    execution.save(update_fields=['status', 'date_start'])
    try:
        payload, table, range_info = build_report_content(report.tp, filters=report.filters, days=report.range_days)
        report_title, report_url = build_report_url(report)
        recipients = list(report.recipients.all())
        with tmp_to_org(report.org_id):
            for user in recipients:
                subscription = UserMsgSubscription.objects.filter(user=user).first()
                receive_backends = subscription.receive_backends if subscription else []
                mapper = ReportLinkMsg(report_title, report_url).get_backend_msg_mapper(receive_backends)
                if not mapper:
                    ReportSendRecord.objects.create(
                        org_id=report.org_id,
                        execution=execution,
                        receiver=user.username,
                        report_url=report_url,
                        is_success=False,
                        error='No available receive backend',
                        detail=f'Report: {report_title}\nReceiver: {user.username}\nURL: {report_url}',
                        created_by='System',
                    )
                    continue
                for backend, backend_payload in mapper.items():
                    ok = True
                    err = ''
                    try:
                        client = BACKEND(backend).client()
                        client.send_msg(User.objects.filter(id=user.id), **backend_payload)
                    except Exception as exc:
                        ok = False
                        err = str(exc)
                    ReportSendRecord.objects.create(
                        org_id=report.org_id,
                        execution=execution,
                        backend=str(backend),
                        receiver=user.username,
                        report_url=report_url,
                        is_success=ok,
                        error=err,
                        detail='\n'.join([
                            f'Report: {report_title}',
                            f'Receiver: {user.username}',
                            f'Backend: {backend}',
                            f'URL: {report_url}',
                            f'Status: {"success" if ok else "failed"}',
                            f'Error: {err}' if err else '',
                        ]).strip(),
                        created_by='System',
                    )
        finish_execution(execution, Status.success, {
            'report_url': report_url,
            'date_from': str(range_info['start']),
            'date_to': str(range_info['end']),
            'table_rows_count': len(table['rows']),
            'payload_keys': list(payload.keys()),
        })
    except Exception as exc:
        finish_execution(execution, Status.failed, {'error': str(exc)})
        logger.exception('Execute report failed')


@shared_task
@after_app_ready_start
def sync_report_periodic_tasks():
    tasks = {}
    for report in Report.objects.filter(is_periodic=True, is_active=True):
        name, task, args, kwargs = report.get_register_task()
        interval = report.interval * 3600 if report.interval and not report.crontab else None
        tasks[name] = {
            'task': task,
            'interval': interval,
            'crontab': report.crontab or None,
            'args': args,
            'kwargs': kwargs,
            'enabled': True,
            'start_time': report.start_time,
        }
    if tasks:
        create_or_update_celery_periodic_tasks(tasks)


@shared_task
def clean_report_send_records():
    keep_days = getattr(settings, 'AUDIT_REPORT_SEND_RECORD_KEEP_DAYS', 200)
    expired_time = timezone.now() - timezone.timedelta(days=int(keep_days))
    ReportSendRecord.objects.filter(date_created__lt=expired_time).delete()