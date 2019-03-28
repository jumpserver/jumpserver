import json

from django.db import models
from django.core.cache import cache
from django.db.utils import ProgrammingError, OperationalError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.utils import get_signer

signer = get_signer()


class SettingQuerySet(models.QuerySet):
    def __getattr__(self, item):
        instances = self.filter(name=item)
        if len(instances) == 1:
            return instances[0]
        else:
            return Setting()


class SettingManager(models.Manager):
    def get_queryset(self):
        return SettingQuerySet(self.model, using=self._db)


class Setting(models.Model):
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    value = models.TextField(verbose_name=_("Value"))
    category = models.CharField(max_length=128, default="default")
    encrypted = models.BooleanField(default=False)
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True)
    comment = models.TextField(verbose_name=_("Comment"))

    objects = SettingManager()

    def __str__(self):
        return self.name

    def __getattr__(self, item):
        return cache.get(item)

    @property
    def cleaned_value(self):
        try:
            value = self.value
            if self.encrypted:
                value = signer.unsign(value)
            if not value:
                return None
            value = json.loads(value)
            return value
        except json.JSONDecodeError:
            return None

    @cleaned_value.setter
    def cleaned_value(self, item):
        try:
            v = json.dumps(item)
            if self.encrypted:
                v = signer.sign(v)
            self.value = v
        except json.JSONDecodeError as e:
            raise ValueError("Json dump error: {}".format(str(e)))

    @classmethod
    def save_storage(cls, name, data):
        """
        :param name: TERMINAL_REPLAY_STORAGE or TERMINAL_COMMAND_STORAGE
        :param data: {}
        :return: Setting object
        """
        obj = cls.objects.filter(name=name).first()
        if not obj:
            obj = cls()
            obj.name = name
            obj.encrypted = True
            obj.cleaned_value = data
        else:
            value = obj.cleaned_value
            if value is None:
                value = {}
            value.update(data)
            obj.cleaned_value = value
        obj.save()
        return obj

    @classmethod
    def delete_storage(cls, name, storage_name):
        """
        :param name: TERMINAL_REPLAY_STORAGE or TERMINAL_COMMAND_STORAGE
        :param storage_name: ""
        :return: bool
        """
        obj = cls.objects.filter(name=name).first()
        if not obj:
            return False
        value = obj.cleaned_value
        value.pop(storage_name, '')
        obj.cleaned_value = value
        obj.save()
        return True

    @classmethod
    def refresh_all_settings(cls):
        try:
            settings_list = cls.objects.all()
            for setting in settings_list:
                setting.refresh_setting()
        except (ProgrammingError, OperationalError):
            pass

    def refresh_setting(self):
        setattr(settings, self.name, self.cleaned_value)
        if self.name == "AUTH_LDAP":
            if self.cleaned_value and settings.AUTH_LDAP_BACKEND not in settings.AUTHENTICATION_BACKENDS:
                old_setting = settings.AUTHENTICATION_BACKENDS
                old_setting.insert(0, settings.AUTH_LDAP_BACKEND)
                settings.AUTHENTICATION_BACKENDS = old_setting
            elif not self.cleaned_value and settings.AUTH_LDAP_BACKEND in settings.AUTHENTICATION_BACKENDS:
                old_setting = settings.AUTHENTICATION_BACKENDS
                old_setting.remove(settings.AUTH_LDAP_BACKEND)
                settings.AUTHENTICATION_BACKENDS = old_setting

    class Meta:
        db_table = "settings_setting"
        verbose_name = _("Setting")
