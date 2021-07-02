from django.db import models
from django.utils.translation import ugettext_lazy as _


class RoleTypeChoices(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')
    app = 'app', _('Application')
