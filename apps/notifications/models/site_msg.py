from django.db import models

from common.db.models import JMSBaseModel

__all__ = ('SiteMessage', 'MessageContent')


class SiteMessage(JMSBaseModel):
    content = models.ForeignKey('notifications.MessageContent', on_delete=models.CASCADE,
                                db_constraint=False, related_name='messages')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, db_constraint=False)
    has_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(default=None, null=True)
    comment = ''


class MessageContent(JMSBaseModel):
    subject = models.CharField(max_length=1024)
    message = models.TextField()
    users = models.ManyToManyField(
        'users.User', through=SiteMessage,
        related_name='recv_site_messages'
    )
    groups = models.ManyToManyField('users.UserGroup')
    is_broadcast = models.BooleanField(default=False)
    sender = models.ForeignKey(
        'users.User', db_constraint=False, on_delete=models.DO_NOTHING, null=True, default=None,
        related_name='send_site_message'
    )
    comment = ''

    has_read = False
    read_at = None
