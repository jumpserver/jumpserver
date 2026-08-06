from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from ops.mixin import PeriodTaskModelMixin
from orgs.mixins.models import JMSOrgBaseModel


class Conversation(JMSOrgBaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        ARCHIVED = 'archived', _('Archived')

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='chat_ai_conversations',
        verbose_name=_('User')
    )
    title = models.CharField(max_length=256, blank=True, default='', verbose_name=_('Title'))
    model = models.CharField(max_length=128, blank=True, default='', verbose_name=_('Model'))
    assistant = models.CharField(max_length=32, blank=True, default='general', verbose_name=_('Assistant'))
    scheduled_report = models.ForeignKey(
        'ScheduledReport', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='conversations', verbose_name=_('Scheduled report')
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE,
        verbose_name=_('Status')
    )

    class Meta:
        db_table = 'chat_ai_conversation'
        ordering = ('-date_updated',)
        indexes = [
            models.Index(fields=('user', 'org_id', '-date_updated')),
            models.Index(fields=('date_updated',), name='chat_ai_con_updated_idx'),
        ]
        verbose_name = _('Chat AI conversation')


class Message(JMSBaseModel):
    class Role(models.TextChoices):
        SYSTEM = 'system', _('System')
        USER = 'user', _('User')
        ASSISTANT = 'assistant', _('Assistant')
        TOOL = 'tool', _('Tool')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        STREAMING = 'streaming', _('Streaming')
        AWAITING_APPROVAL = 'awaiting_approval', _('Awaiting approval')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages',
        verbose_name=_('Conversation')
    )
    role = models.CharField(max_length=16, choices=Role.choices, verbose_name=_('Role'))
    content = models.TextField(blank=True, default='', verbose_name=_('Content'))
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.PENDING,
        verbose_name=_('Status')
    )
    model = models.CharField(max_length=128, blank=True, default='', verbose_name=_('Model'))
    input_tokens = models.PositiveIntegerField(default=0, verbose_name=_('Input tokens'))
    output_tokens = models.PositiveIntegerField(default=0, verbose_name=_('Output tokens'))
    error = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('Error'))
    result_cards = models.JSONField(default=list, blank=True, verbose_name=_('Result cards'))
    regenerated_from = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='regenerations', verbose_name=_('Regenerated from')
    )

    class Meta:
        db_table = 'chat_ai_message'
        ordering = ('date_created',)
        indexes = [
            models.Index(fields=('conversation', 'date_created')),
            models.Index(fields=('date_created',), name='chat_ai_msg_created_idx'),
        ]
        verbose_name = _('Chat AI message')


class MessageImage(JMSBaseModel):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='images',
        verbose_name=_('Message')
    )
    file = models.FileField(
        upload_to='chat_ai/images/%Y/%m/%d/', max_length=512,
        verbose_name=_('File')
    )
    name = models.CharField(max_length=255, verbose_name=_('Name'))
    content_type = models.CharField(max_length=64, verbose_name=_('Content type'))
    size = models.PositiveIntegerField(default=0, verbose_name=_('Size'))

    class Meta:
        db_table = 'chat_ai_message_image'
        ordering = ('date_created',)
        indexes = [
            models.Index(fields=('date_created',), name='chat_ai_img_created_idx'),
        ]
        verbose_name = _('Chat AI message image')


@receiver(post_delete, sender=MessageImage)
def delete_message_image_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


class MessageFile(JMSBaseModel):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='files',
        verbose_name=_('Message')
    )
    file = models.FileField(
        upload_to='chat_ai/files/%Y/%m/%d/', max_length=512,
        verbose_name=_('File')
    )
    name = models.CharField(max_length=255, verbose_name=_('Name'))
    content_type = models.CharField(max_length=128, verbose_name=_('Content type'))
    size = models.PositiveIntegerField(default=0, verbose_name=_('Size'))
    extracted_text = models.TextField(blank=True, default='', verbose_name=_('Extracted text'))

    class Meta:
        db_table = 'chat_ai_message_file'
        ordering = ('date_created',)
        indexes = [
            models.Index(fields=('date_created',), name='chat_ai_file_created_idx'),
        ]
        verbose_name = _('Chat AI message file')


@receiver(post_delete, sender=MessageFile)
def delete_message_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)


class AgentRun(JMSBaseModel):
    class Status(models.TextChoices):
        QUEUED = 'queued', _('Queued')
        RUNNING = 'running', _('Running')
        AWAITING_APPROVAL = 'awaiting_approval', _('Awaiting approval')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    conversation = models.ForeignKey(
        Conversation, null=True, on_delete=models.SET_NULL, related_name='agent_runs',
        verbose_name=_('Conversation')
    )
    assistant_message = models.OneToOneField(
        Message, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='agent_run', verbose_name=_('Assistant message')
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='chat_ai_agent_runs',
        verbose_name=_('User')
    )
    org_id = models.CharField(max_length=36, db_index=True, verbose_name=_('Organization'))
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.QUEUED,
        verbose_name=_('Status')
    )
    task_id = models.CharField(
        max_length=255, blank=True, default='', db_index=True,
        verbose_name=_('Celery task ID')
    )
    step_count = models.PositiveIntegerField(default=0, verbose_name=_('Step count'))
    api_call_count = models.PositiveIntegerField(default=0, verbose_name=_('API call count'))
    search_summary = models.JSONField(default=list, blank=True, verbose_name=_('API search summary'))
    input_tokens = models.PositiveIntegerField(default=0, verbose_name=_('Input tokens'))
    output_tokens = models.PositiveIntegerField(default=0, verbose_name=_('Output tokens'))
    model_duration_ms = models.PositiveIntegerField(default=0, verbose_name=_('Model duration'))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Started at'))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Finished at'))
    error = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('Error'))

    class Meta:
        db_table = 'chat_ai_agent_run'
        ordering = ('-started_at',)
        indexes = [
            models.Index(fields=('user', 'org_id', '-started_at')),
            models.Index(
                fields=('user', 'status', 'date_created'),
                name='chat_ai_age_user_id_queued_idx',
            ),
            models.Index(fields=('date_updated',), name='chat_ai_run_updated_idx'),
        ]
        verbose_name = _('Chat AI agent run')


class ApiCallAudit(JMSBaseModel):
    agent_run = models.ForeignKey(
        AgentRun, null=True, on_delete=models.SET_NULL, related_name='api_call_audits',
        verbose_name=_('Agent run')
    )
    conversation = models.ForeignKey(
        Conversation, null=True, on_delete=models.SET_NULL, related_name='api_call_audits',
        verbose_name=_('Conversation')
    )
    message = models.ForeignKey(
        Message, null=True, on_delete=models.SET_NULL, related_name='api_call_audits',
        verbose_name=_('Message')
    )
    approval = models.ForeignKey(
        'Approval', null=True, on_delete=models.SET_NULL, related_name='api_call_audits',
        verbose_name=_('Approval')
    )
    user = models.ForeignKey(
        'users.User', null=True, on_delete=models.SET_NULL, related_name='chat_ai_api_call_audits',
        verbose_name=_('User')
    )
    org_id = models.CharField(max_length=36, db_index=True, verbose_name=_('Organization'))
    operation_id = models.CharField(max_length=256, db_index=True, verbose_name=_('Operation ID'))
    method = models.CharField(max_length=8, verbose_name=_('Method'))
    path = models.CharField(max_length=1024, verbose_name=_('Path'))
    request_summary = models.JSONField(default=dict, blank=True, verbose_name=_('Request summary'))
    response_summary = models.JSONField(default=dict, blank=True, verbose_name=_('Response summary'))
    status_code = models.PositiveIntegerField(default=0, verbose_name=_('Status code'))
    risk_level = models.CharField(max_length=32, default='read', verbose_name=_('Risk level'))
    duration_ms = models.PositiveIntegerField(default=0, verbose_name=_('Duration'))
    error = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('Error'))

    class Meta:
        db_table = 'chat_ai_api_call_audit'
        ordering = ('-date_created',)
        indexes = [
            models.Index(fields=('operation_id', '-date_created')),
            models.Index(fields=('user', 'org_id', '-date_created')),
            models.Index(fields=('date_created',), name='chat_ai_audit_created_idx'),
        ]
        verbose_name = _('Chat AI API call audit')


class Approval(JMSBaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        CONFIRMED = 'confirmed', _('Confirmed')
        CANCELLED = 'cancelled', _('Cancelled')
        EXPIRED = 'expired', _('Expired')
        FAILED = 'failed', _('Failed')

    conversation = models.ForeignKey(
        Conversation, null=True, on_delete=models.SET_NULL, related_name='approvals',
        verbose_name=_('Conversation')
    )
    agent_run = models.ForeignKey(
        AgentRun, null=True, on_delete=models.SET_NULL, related_name='approvals',
        verbose_name=_('Agent run')
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='chat_ai_approvals',
        verbose_name=_('User')
    )
    org_id = models.CharField(max_length=36, db_index=True, verbose_name=_('Organization'))
    operation_id = models.CharField(max_length=256, verbose_name=_('Operation ID'))
    method = models.CharField(max_length=8, verbose_name=_('Method'))
    path = models.CharField(max_length=1024, verbose_name=_('Path'))
    request_payload = models.JSONField(default=dict, verbose_name=_('Request payload'))
    request_hash = models.CharField(max_length=64, verbose_name=_('Request hash'))
    nonce = models.CharField(max_length=64, unique=True, verbose_name=_('Nonce'))
    signing_key_id = models.CharField(max_length=64, default='v1', verbose_name=_('Signing key ID'))
    signature = models.CharField(max_length=64, verbose_name=_('Signature'))
    risk_level = models.CharField(max_length=32, default='write', verbose_name=_('Risk level'))
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.PENDING,
        verbose_name=_('Status')
    )
    confirmed_by = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='confirmed_chat_ai_approvals', verbose_name=_('Confirmed by')
    )
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Confirmed at'))
    expires_at = models.DateTimeField(db_index=True, verbose_name=_('Expires at'))
    result_summary = models.JSONField(default=dict, blank=True, verbose_name=_('Result summary'))
    error = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('Error'))

    class Meta:
        db_table = 'chat_ai_approval'
        ordering = ('-date_created',)
        indexes = [
            models.Index(fields=('user', 'org_id', 'status')),
            models.Index(fields=('date_updated',), name='chat_ai_appr_updated_idx'),
        ]
        verbose_name = _('Chat AI approval')


class ScheduledReport(JMSOrgBaseModel, PeriodTaskModelMixin):
    is_periodic = models.BooleanField(default=True, verbose_name=_('Periodic run'))
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='chat_ai_scheduled_reports',
        verbose_name=_('User')
    )
    prompt = models.TextField(verbose_name=_('Prompt'))
    assistant = models.CharField(max_length=32, default='ops', verbose_name=_('Assistant'))
    web_search = models.BooleanField(default=False, verbose_name=_('Web search'))
    notify = models.BooleanField(default=True, verbose_name=_('Notify'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    last_status = models.CharField(max_length=32, blank=True, default='', verbose_name=_('Last status'))
    last_error = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('Last error'))

    @property
    def interval_ratio(self):
        return 3600, 'h'

    def get_register_task(self):
        from .tasks import run_scheduled_chat_ai_report

        name = f'chat_ai_scheduled_report_{self.id}'
        return name, run_scheduled_chat_ai_report.name, (str(self.id),), {}

    class Meta:
        db_table = 'chat_ai_scheduled_report'
        ordering = ('-date_updated',)
        unique_together = (('user', 'org_id', 'name'),)
        indexes = [models.Index(fields=('user', 'org_id', 'is_active'))]
        verbose_name = _('Chat AI scheduled report')
