from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import OneToOneField, Count

from common.utils import lazyproperty
from .models import LabeledResource

__all__ = ['LabeledMixin']


class LabeledMixin(models.Model):
    labels = GenericRelation(LabeledResource, object_id_field='res_id', content_type_field='res_type')

    class Meta:
        abstract = True

    @classmethod
    def label_model(cls):
        pk_field = cls._meta.pk
        model = cls
        if isinstance(pk_field, OneToOneField):
            model = pk_field.related_model
        return model

    @lazyproperty
    def real(self):
        pk_field = self._meta.pk
        if isinstance(pk_field, OneToOneField):
            return getattr(self, pk_field.name)
        return self

    @property
    def res_labels(self):
        return self.real.labels

    @res_labels.setter
    def res_labels(self, value):
        self.real.labels.set(value, bulk=False)

    @classmethod
    def filter_resources_by_labels(cls, resources, label_ids):
        return cls._get_filter_res_by_labels_m2m_all(resources, label_ids)

    @classmethod
    def _get_filter_res_by_labels_m2m_in(cls, resources, label_ids):
        return resources.filter(label_id__in=label_ids)

    @classmethod
    def _get_filter_res_by_labels_m2m_all(cls, resources, label_ids):
        if len(label_ids) == 1:
            return cls._get_filter_res_by_labels_m2m_in(resources, label_ids)

        resources = resources.filter(label_id__in=label_ids) \
            .values('res_id') \
            .order_by('res_id') \
            .annotate(count=Count('res_id', distinct=True)) \
            .values('res_id', 'count') \
            .filter(count=len(label_ids))
        return resources

    @classmethod
    def get_labels_filter_attr_q(cls, value, match):
        resources = LabeledResource.objects.all()
        if not value:
            return None

        if match != 'm2m_all':
            resources = cls._get_filter_res_by_labels_m2m_in(resources, value)
        else:
            resources = cls._get_filter_res_by_labels_m2m_all(resources, value)
        res_ids = set(resources.values_list('res_id', flat=True))
        return models.Q(id__in=res_ids)
