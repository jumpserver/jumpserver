from django.utils.translation import gettext_lazy as _

from common.db import models
from orgs.mixins.models import OrgModelMixin


class K8sApp(OrgModelMixin, models.JMSModel):
    class TYPE(models.ChoiceSet):
        K8S = 'k8s', _('Kubernetes')

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    type = models.CharField(
        default=TYPE.K8S, choices=TYPE.choices,
        max_length=128, verbose_name=_('Type')
    )
    cluster = models.CharField(max_length=1024, verbose_name=_('Cluster'))
    comment = models.TextField(
        max_length=128, default='', blank=True, verbose_name=_('Comment')
    )

    def __str__(self):
        return self.name

    class Meta:
        unique_together = [('org_id', 'name'), ]
        verbose_name = _('KubernetesApp')
        ordering = ('name', )
