from django.db  import models
from users.models import User
from django.utils.translation import ugettext_lazy as _


class AuthDevice(models.Model):
    ip = models.GenericIPAddressField(max_length=32, verbose_name=_('IP'), db_index=True)
    user = models.ForeignKey(User, verbose_name=_('User'), related_name='auth_devices')
