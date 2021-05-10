from datetime import datetime

from django.db import models

from common.db.models import JMSBaseModel


class SiteMessage(JMSBaseModel):
    subject = models.CharField(max_length=1024)
    message = models.TextField()
    users = models.ManyToManyField('users.User', through='site_message.SiteMessageUsers')
    groups = models.ManyToManyField('users.UserGroup')
    is_broadcast = models.BooleanField(default=False)
    sender = models.ForeignKey('users.User', db_constraint=False, on_delete=models.DO_NOTHING, null=True, default=None)


class SiteMessageUsers(JMSBaseModel):
    sitemessage = models.ForeignKey('site_message.SiteMessage', on_delete=models.CASCADE, db_constraint=False, related_name='m2m_sitemessageusers')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, db_constraint=False, related_name='m2m_sitemessageusers')
    has_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(default=datetime.min)
