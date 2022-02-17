from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AclsConfig(AppConfig):
    name = 'acls'
    verbose_name = _('Acls')
