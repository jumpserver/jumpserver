from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from .models import LabeledResource

__all__ = ['LabeledMixin']


class LabeledMixin(models.Model):
    _labels = GenericRelation(LabeledResource, object_id_field='res_id', content_type_field='res_type')

    class Meta:
        abstract = True

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, value):
        self._labels.set(value, bulk=False)
