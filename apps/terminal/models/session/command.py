from __future__ import unicode_literals

from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _

from terminal.backends.command.models import AbstractSessionCommand


class CommandManager(models.Manager):
    def bulk_create(self, objs, **kwargs):
        resp = super().bulk_create(objs, **kwargs)
        for i in objs:
            post_save.send(i.__class__, instance=i, created=True)
        return resp


class Command(AbstractSessionCommand):
    objects = CommandManager()

    @classmethod
    def generate_fake(cls, count=100, org=None):
        import uuid
        import datetime
        from orgs.models import Organization
        from common.utils import random_string

        if not org:
            org = Organization.default()

        d = datetime.datetime.now() - datetime.timedelta(days=1)
        commands = [
            cls(**{
                'user': random_string(6),
                'asset': random_string(10),
                'account': random_string(6),
                'session': str(uuid.uuid4()),
                'input': random_string(16),
                'output': random_string(64),
                'timestamp': int(d.timestamp()),
                'org_id': str(org.id)
            })
            for i in range(count)
        ]
        cls.objects.bulk_create(commands)
        print(f'Create {len(commands)} commands of org ({org})')

    @classmethod
    def from_dict(cls, d):
        self = cls()
        for k, v in d.items():
            setattr(self, k, v)
        return self

    @classmethod
    def from_multi_dict(cls, l):
        commands = []
        for d in l:
            command = cls.from_dict(d)
            commands.append(command)
        return commands

    class Meta:
        db_table = "terminal_command"
        ordering = ('-timestamp',)
        verbose_name = _('Command record')
