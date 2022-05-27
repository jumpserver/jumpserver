from django.db import models, transaction
from django.db.transaction import atomic as db_atomic


class ForeignKey(models.ForeignKey):
    def __init__(self, *args, **kwargs):
        kwargs['db_constraint'] = False
        super().__init__(*args, **kwargs)


def atomic(using=None, savepoint=False):
    return db_atomic(using=using, savepoint=savepoint)


transaction.atomic = atomic
models.ForeignKey = ForeignKey
