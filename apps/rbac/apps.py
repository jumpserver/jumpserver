from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class RBACConfig(AppConfig):
    name = 'rbac'
    verbose_name = _('RBAC')
