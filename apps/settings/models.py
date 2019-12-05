import json

from django.db import models
from django.db.utils import ProgrammingError, OperationalError
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

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
    cache_key_prefix = '_SETTING_'

    def __str__(self):
        return self.name

    @classmethod
    def get(cls, item):
        cached = cls.get_from_cache(item)
        if cached is not None:
            return cached
        instances = cls.objects.filter(name=item)
        if len(instances) == 1:
            s = instances[0]
            s.refresh_setting()
            return s.cleaned_value
        return None

    @classmethod
    def get_from_cache(cls, item):
        key = cls.cache_key_prefix + item
        cached = cache.get(key)
        return cached

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
    def refresh_all_settings(cls):
        try:
            settings_list = cls.objects.all()
            for setting in settings_list:
                setting.refresh_setting()
        except (ProgrammingError, OperationalError):
            pass

    def refresh_setting(self):
        key = self.cache_key_prefix + self.name
        cache.set(key, self.cleaned_value, None)

    class Meta:
        db_table = "settings_setting"
        verbose_name = _("Setting")
