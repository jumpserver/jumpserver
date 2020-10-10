from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class NamespacesConfig(AppConfig):
    name = 'namespaces'
    verbose_name = _('Namespace Management')
