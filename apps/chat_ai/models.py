from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel


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
    record = models.TextField()

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
