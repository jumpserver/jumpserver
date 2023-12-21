from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LabelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'labels'
    verbose_name = _('Labels')
