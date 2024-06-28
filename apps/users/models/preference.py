from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.utils import Encryptor
from common.utils import get_logger

logger = get_logger(__name__)


class Preference(models.Model):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    category = models.CharField(max_length=128, verbose_name=_('Category'))
    value = models.TextField(verbose_name=_("Value"), default='', blank=True)
    encrypted = models.BooleanField(default=False, verbose_name=_('Encrypted'))
    user = models.ForeignKey(
        'users.User', verbose_name=_("Users"), related_name='preferences', on_delete=models.CASCADE
    )

    def __str__(self):
        return f'{self.name}({self.user.username})'

    @classmethod
    def encrypt(cls, value):
        return Encryptor(value).encrypt()

    @classmethod
    def decrypt(cls, value):
        return Encryptor(value).decrypt()

    @property
    def decrypt_value(self):
        if self.encrypted:
            return self.decrypt(self.value)
        return self.value

    class Meta:
        db_table = "users_preference"
        verbose_name = _("Preference")
        unique_together = [('name', 'user_id')]


class PreferenceManager:
    def __init__(self, user):
        self.user = user

    def get(self, name, category=None):
        query = {'name': name, 'user': self.user}
        if category:
            query['category'] = category
        return Preference.objects.filter(**query).first()

    def get_value(self, name, category=None, default=None):
        preference = self.get(name, category)
        if preference:
            return preference.decrypt_value
        return default

    def set(self, name, value, category=None, encrypted=False):
        query = {'name': name, 'user': self.user}
        if category:
            query['category'] = category
        if encrypted:
            value = Preference.encrypt(value)
        preference, __ = Preference.objects.update_or_create(
            defaults={'value': value, 'encrypted': encrypted},
            **query
        )
        return preference

    def set_value(self, name, value, category=None, encrypted=False):
        preference = self.set(name, value, category, encrypted)
        return preference.decrypt_value

    def as_dict(self):
        return {pref.name: pref.decrypt_value for pref in self.user.preferences.all()}
