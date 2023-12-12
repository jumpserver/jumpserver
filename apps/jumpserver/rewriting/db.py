import os
import sys

from django.db import models, transaction
from django.db.transaction import atomic as db_atomic


class ForeignKey(models.ForeignKey):
    def __init__(self, *args, **kwargs):
        kwargs['db_constraint'] = False
        super().__init__(*args, **kwargs)


def atomic(using=None, savepoint=False):
    return db_atomic(using=using, savepoint=savepoint)


class OneToOneField(models.OneToOneField, ForeignKey):
    def __init__(self, *args, **kwargs):
        kwargs['unique'] = False
        if os.getenv('DB_CONSTRAINT', '1') == '0':
            kwargs['db_constraint'] = False
        ForeignKey.__init__(self, *args, **kwargs)


def set_db_constraint():
    if os.getenv('DB_CONSTRAINT', '1') != '0':
        return
    if len(sys.argv) >= 2 and sys.argv[1] in ['makemigrations', 'check']:
        return
    print("Set foreignkey db constraint False")
    transaction.atomic = atomic
    models.ForeignKey = ForeignKey
    models.OneToOneField = OneToOneField


set_db_constraint()
