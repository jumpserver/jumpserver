from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AclsConfig(AppConfig):
    name = 'acls'
    verbose_name = _('Acls')
