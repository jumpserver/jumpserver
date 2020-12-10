from __future__ import unicode_literals

from django.db import models
from django.db.models.signals import post_save
from ..backends.command.models import AbstractSessionCommand


class CommandManager(models.Manager):
    def bulk_create(self, objs, **kwargs):
        resp = super().bulk_create(objs, **kwargs)
        for i in objs:
            post_save.send(i.__class__, instance=i, created=True)
        return resp


class Command(AbstractSessionCommand):
    objects = CommandManager()

    class Meta:
        db_table = "terminal_command"
        ordering = ('-timestamp',)
