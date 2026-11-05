from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.fields import UnicodeCharField, UnicodeTextField
from common.db.models import JMSBaseModel
from orgs.mixins.models import OrgModelMixin


class RuntimeStore(JMSBaseModel):
    """Global revision head for Kael's durable runtime journal."""

    key = models.CharField(max_length=64, unique=True, default='default')
    revision = models.PositiveBigIntegerField(default=0)
    snapshot_revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        db_table = 'chat_ai_runtime_store'
        default_permissions = ()
        permissions = (
            ('use_chatai', _('Can use Chat AI')),
        )
        verbose_name = _('Chat AI runtime store')


class RuntimeStoreRecord(JMSBaseModel):
    """An opaque, checksummed Kael JSONL journal record."""

    store = models.ForeignKey(
        RuntimeStore, on_delete=models.CASCADE, related_name='records',
        verbose_name=_('Runtime store'),
    )
    revision = models.PositiveBigIntegerField()
    commit_id = models.UUIDField(unique=True)
    snapshot = models.BooleanField(default=False)
    record = UnicodeTextField()

    class Meta:
        db_table = 'chat_ai_runtime_store_record'
        default_permissions = ()
        ordering = ('revision',)
        constraints = [
            models.UniqueConstraint(
                fields=('store', 'revision'),
                name='chat_ai_rt_store_rev_uniq',
            ),
        ]
        indexes = [
            models.Index(
                fields=('store', 'snapshot', '-revision'),
                name='chat_ai_rt_snap_rev_idx',
            ),
        ]
        verbose_name = _('Chat AI runtime store record')


class AuditConversation(OrgModelMixin):
    """Independent audit history; runtime deletion must not delete this record."""

    id = models.UUIDField(primary_key=True)
    subject_id = models.UUIDField()
    subject_name = UnicodeCharField(max_length=128, blank=True)
    subject_username = UnicodeCharField(max_length=128, blank=True)
    title = UnicodeTextField(blank=True)
    assistant = models.CharField(max_length=64, blank=True)
    profile = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=32, blank=True)
    date_created = models.DateTimeField()
    date_updated = models.DateTimeField()
    source_revision = models.PositiveBigIntegerField()

    class Meta:
        default_permissions = ('view',)
        ordering = ('-date_updated', '-id')
        indexes = [models.Index(fields=('org_id', '-date_updated'), name='chat_ai_audit_org_updated_idx')]
        verbose_name = _('Chat AI conversation audit')


class AuditMessage(OrgModelMixin):
    id = models.CharField(max_length=128, primary_key=True)
    conversation = models.ForeignKey(AuditConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=16)
    content = UnicodeTextField(blank=True)
    status = models.CharField(max_length=32, blank=True)
    error = UnicodeTextField(blank=True)
    input_tokens = models.PositiveBigIntegerField(default=0)
    output_tokens = models.PositiveBigIntegerField(default=0)
    date_created = models.DateTimeField()
    source_revision = models.PositiveBigIntegerField()

    class Meta:
        default_permissions = ()
        ordering = ('date_created', 'id')
        indexes = [
            models.Index(
                fields=('conversation', 'role', 'date_created'),
                name='chat_ai_audit_msg_stats_idx',
            ),
        ]
        verbose_name = _('Chat AI audit message')
