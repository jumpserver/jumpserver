from django.db import models
from django.utils.translation import gettext_lazy as _


class Permission(models.Model):
    class Meta:
        permissions = [
            ('view_resourcestatistics', _('Can view resource statistics'))
        ]
