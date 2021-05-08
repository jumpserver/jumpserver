from datetime import datetime

from django.db import models

from common.db.models import JMSBaseModel


class SiteMessage(JMSBaseModel):
    text = models.TextField()
    users = models.ManyToManyField('users.User', through='site_message.SiteMessageUsers')
    groups = models.ManyToManyField('users.UserGroup')
    is_broadcast = models.BooleanField(default=False)


class SiteMessageUsers(JMSBaseModel):
    sitemessage = models.ForeignKey('site_message.SiteMessage', on_delete=models.CASCADE, db_constraint=False)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, db_constraint=False)
    has_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(default=datetime.min)
