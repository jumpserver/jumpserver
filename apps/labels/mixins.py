from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import OneToOneField

from .models import LabeledResource

__all__ = ['LabeledMixin']


class LabeledMixin(models.Model):
    _labels = GenericRelation(LabeledResource, object_id_field='res_id', content_type_field='res_type')

    class Meta:
        abstract = True

    @classmethod
    def label_model(cls):
        pk_field = cls._meta.pk
        model = cls
        if isinstance(pk_field, OneToOneField):
            model = pk_field.related_model
        return model

    @property
    def real(self):
        pk_field = self._meta.pk
        if isinstance(pk_field, OneToOneField):
            return getattr(self, pk_field.name)
        return self

    @property
    def labels(self):
        return self.real._labels

    @labels.setter
    def labels(self, value):
        self.real._labels.set(value, bulk=False)
