import json

import ldap
from django.db import models
from django.db.utils import ProgrammingError, OperationalError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django_auth_ldap.config import LDAPSearch, LDAPSearchUnion

from .utils import get_signer

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
        instances = self.__class__.objects.filter(name=item)
        if len(instances) == 1:
            return instances[0].cleaned_value
        else:
            return None

    @property
    def cleaned_value(self):
        try:
            value = self.value
            if self.encrypted:
                value = signer.unsign(value)
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
        setattr(settings, self.name, self.cleaned_value)

        if self.name == "AUTH_LDAP":
            if self.cleaned_value and settings.AUTH_LDAP_BACKEND not in settings.AUTHENTICATION_BACKENDS:
                settings.AUTHENTICATION_BACKENDS.insert(0, settings.AUTH_LDAP_BACKEND)
            elif not self.cleaned_value and settings.AUTH_LDAP_BACKEND in settings.AUTHENTICATION_BACKENDS:
                settings.AUTHENTICATION_BACKENDS.remove(settings.AUTH_LDAP_BACKEND)

        if self.name == "AUTH_LDAP_SEARCH_FILTER":
            settings.AUTH_LDAP_USER_SEARCH_UNION = [
                LDAPSearch(USER_SEARCH, ldap.SCOPE_SUBTREE, settings.AUTH_LDAP_SEARCH_FILTER)
                for USER_SEARCH in str(settings.AUTH_LDAP_SEARCH_OU).split("|")
            ]
            settings.AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(*settings.AUTH_LDAP_USER_SEARCH_UNION)

    class Meta:
        db_table = "settings"


common_settings = Setting()
