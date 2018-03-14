import json

import ldap
from django.db import models
from django.db.utils import ProgrammingError, OperationalError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django_auth_ldap.config import LDAPSearch


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
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True)
    comment = models.TextField(verbose_name=_("Comment"))

    objects = SettingManager()

    def __str__(self):
        return self.name

    @property
    def cleaned_value(self):
        try:
            return json.loads(self.value)
        except json.JSONDecodeError:
            return None

    @cleaned_value.setter
    def cleaned_value(self, item):
        try:
            v = json.dumps(item)
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
        try:
            value = json.loads(self.value)
        except json.JSONDecodeError:
            return
        setattr(settings, self.name, value)

        if self.name == "AUTH_LDAP":
            if self.cleaned_value and settings.AUTH_LDAP_BACKEND not in settings.AUTHENTICATION_BACKENDS:
                settings.AUTHENTICATION_BACKENDS.insert(0, settings.AUTH_LDAP_BACKEND)
            elif not self.cleaned_value and settings.AUTH_LDAP_BACKEND in settings.AUTHENTICATION_BACKENDS:
                settings.AUTHENTICATION_BACKENDS.remove(settings.AUTH_LDAP_BACKEND)

        if self.name == "AUTH_LDAP_SEARCH_FILTER":
            settings.AUTH_LDAP_USER_SEARCH = LDAPSearch(
                settings.AUTH_LDAP_SEARCH_OU, ldap.SCOPE_SUBTREE,
                settings.AUTH_LDAP_SEARCH_FILTER,
            )

    class Meta:
        db_table = "settings"
