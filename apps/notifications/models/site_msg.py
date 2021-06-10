from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSModel

__all__ = ('SiteMessageUsers', 'SiteMessage')


class SiteMessageUsers(JMSModel):
    sitemessage = models.ForeignKey('notifications.SiteMessage', on_delete=models.CASCADE, db_constraint=False, related_name='m2m_sitemessageusers')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, db_constraint=False, related_name='m2m_sitemessageusers')
    has_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(default=None, null=True)


class SiteMessage(JMSModel):
    subject = models.CharField(max_length=1024)
    message = models.TextField()
    users = models.ManyToManyField(
        'users.User', through=SiteMessageUsers, related_name='recv_site_messages'
    )
    groups = models.ManyToManyField('users.UserGroup')
    is_broadcast = models.BooleanField(default=False)
    sender = models.ForeignKey(
        'users.User', db_constraint=False, on_delete=models.DO_NOTHING, null=True, default=None,
        related_name='send_site_message'
    )

    has_read = False
    read_at = None
