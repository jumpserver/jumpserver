import os

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.db.transaction import atomic as db_atomic
from django.db.models.fields.related import OneToOneRel
from django.db.models.fields.related_descriptors import (
    ReverseOneToOneDescriptor, ForwardOneToOneDescriptor
)


def atomic(using=None, savepoint=False):
    return db_atomic(using=using, savepoint=savepoint)


class ForeignKey(models.ForeignKey):
    def __init__(self, *args, **kwargs):
        kwargs['db_constraint'] = False
        super().__init__(*args, **kwargs)


class OneToOneField(ForeignKey):
    # Field flags
    many_to_many = False
    many_to_one = False
    one_to_many = False
    one_to_one = True

    related_accessor_class = ReverseOneToOneDescriptor
    forward_related_accessor_class = ForwardOneToOneDescriptor
    rel_class = OneToOneRel

    description = _("One-to-one relationship")

    def __init__(self, to, on_delete, to_field=None, **kwargs):
        kwargs['unique'] = False
        super().__init__(to, on_delete, to_field=to_field, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if "unique" in kwargs:
            del kwargs['unique']
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        if self.remote_field.parent_link:
            return None
        return super().formfield(**kwargs)

    def save_form_data(self, instance, data):
        if isinstance(data, self.remote_field.model):
            setattr(instance, self.name, data)
        else:
            setattr(instance, self.attname, data)
            # Remote field object must be cleared otherwise Model.save()
            # will reassign attname using the related object pk.
            if data is None:
                setattr(instance, self.name, data)

    def _check_unique(self, **kwargs):
        # Override ForeignKey since check isn't applicable here.
        return []


if os.getenv('FK_CONSTRAINT', '1') == '0':
    transaction.atomic = atomic
    models.ForeignKey = ForeignKey
    models.OneToOneField = OneToOneField
