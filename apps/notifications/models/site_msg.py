from django.db import models

from common.db.models import JMSBaseModel
from ..const import SiteMessageDisplayMode

__all__ = ('SiteMessage', 'MessageContent')


class SiteMessage(JMSBaseModel):
    content = models.ForeignKey('notifications.MessageContent', on_delete=models.CASCADE,
                                db_constraint=False, related_name='messages')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, db_constraint=False)
    has_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(default=None, null=True)
    comment = ''

    def as_data(self):
        return {
            'id': str(self.id),
            'content': self.content.as_data() if self.content else {},
            'has_read': self.has_read,
            'date_created': str(self.date_created)
        }


class MessageContent(JMSBaseModel):
    DisplayMode = SiteMessageDisplayMode

    subject = models.CharField(max_length=1024)
    message = models.TextField()
    users = models.ManyToManyField(
        'users.User', through=SiteMessage,
        related_name='recv_site_messages'
    )
    groups = models.ManyToManyField('users.UserGroup')
    is_broadcast = models.BooleanField(default=False)
    display_mode = models.CharField(
        default=DisplayMode.default,
        choices=DisplayMode.choices,
        max_length=32,
    )
    sender = models.ForeignKey(
        'users.User', db_constraint=False, on_delete=models.DO_NOTHING, null=True, default=None,
        related_name='send_site_message'
    )
    comment = ''

    has_read = False
    read_at = None

    def as_data(self):
        return {
            'id': str(self.id),
            'subject': self.subject,
            'is_broadcast': self.is_broadcast,
            'message': self.message,
            'display_mode': self.display_mode,
            'date_created': str(self.date_created),
            'sender': str(self.sender) if self.sender else ''
        }
    
    def revoke_msg(self):
        if not self.is_broadcast:
            return
        self.is_broadcast = False
        self.save()
