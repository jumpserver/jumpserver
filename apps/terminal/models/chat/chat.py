from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from common.utils import get_logger

logger = get_logger(__name__)

__all__ = ['Chat']


class Chat(JMSBaseModel):
    # id == session_id # 36 chars
    title = models.CharField(max_length=256, verbose_name=_('Title'))
    chat = models.JSONField(default=dict, verbose_name=_('Chat'))
    meta = models.JSONField(default=dict, verbose_name=_('Meta'))
    pinned = models.BooleanField(default=False, verbose_name=_('Pinned'))
    archived = models.BooleanField(default=False, verbose_name=_('Archived'))
    share_id = models.CharField(blank=True, default='', max_length=36)
    folder_id = models.CharField(blank=True, default='', max_length=36)
    socket_id = models.CharField(blank=True, default='', max_length=36)
    user_id = models.CharField(blank=True, default='', max_length=36, db_index=True)

    session_info = models.JSONField(default=dict, verbose_name=_('Session Info'))

    class Meta:
        verbose_name = _('Chat')

    def __str__(self):
        return self.title
