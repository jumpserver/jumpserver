from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.utils import lazyproperty
from orgs.mixins.models import JMSOrgBaseModel


class Label(JMSOrgBaseModel):
    name = models.CharField(max_length=64, verbose_name=_("Name"), db_index=True)
    value = models.CharField(max_length=64, unique=False, verbose_name=_("Value"))
    internal = models.BooleanField(default=False, verbose_name=_("Internal"))

    class Meta:
        unique_together = [('name', 'value', 'org_id')]
        verbose_name = _('Label')

    @lazyproperty
    def res_count(self):
        return self.labeled_resources.count()

    @lazyproperty
    def display_name(self):
        return '{}:{}'.format(self.name, self.value)

    def __str__(self):
        return '{}:{}'.format(self.name, self.value)


class LabeledResource(JMSOrgBaseModel):
    label = models.ForeignKey(
        Label, on_delete=models.CASCADE, related_name='labeled_resources', verbose_name=_("Label")
    )
    res_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    res_id = models.CharField(max_length=36, verbose_name=_("Resource ID"), db_index=True)
    resource = GenericForeignKey('res_type', 'res_id')

    class Meta:
        unique_together = [('label', 'res_type', 'res_id', 'org_id')]
        verbose_name = _('Labeled resource')

    def __str__(self):
        return '{} => {}'.format(self.label, self.resource)
