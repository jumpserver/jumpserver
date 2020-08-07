# coding: utf-8
# 

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from .base import BasePermission

__all__ = [
    'K8sAppPermission',
]


class K8sAppPermission(BasePermission):
    k8s_apps = models.ManyToManyField(
        'applications.K8sApp', related_name='granted_by_permissions',
        blank=True, verbose_name=_("KubernetesApp")
    )
    system_users = models.ManyToManyField(
        'assets.SystemUser', related_name='granted_by_k8s_app_permissions',
        verbose_name=_("System user")
    )

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('KubernetesApp permission')
        ordering = ('name',)

    def get_all_k8s_apps(self):
        return self.k8s_apps.all()

    @lazyproperty
    def k8s_apps_amount(self):
        return self.k8s_apps.count()

    @lazyproperty
    def system_users_amount(self):
        return self.system_users.count()
