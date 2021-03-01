import json

from django.db import models
from django.db.utils import ProgrammingError, OperationalError
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.utils import signer, get_logger

logger = get_logger(__name__)


class SettingQuerySet(models.QuerySet):
    def __getattr__(self, item):
        queryset = list(self)
        instances = [i for i in queryset if i.name == item]
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

    @classmethod
    def refresh_item(cls, name):
        item = cls.objects.filter(name=name).first()
        if not item:
            return
        item.refresh_setting()

    def refresh_setting(self):
        logger.debug(f"Refresh setting: {self.name}")
        if hasattr(self.__class__, f'refresh_{self.name}'):
            getattr(self.__class__, f'refresh_{self.name}')()
        else:
            setattr(settings, self.name, self.cleaned_value)

    @classmethod
    def refresh_AUTH_LDAP(cls):
        setting = cls.objects.filter(name='AUTH_LDAP').first()
        if not setting:
            return
        ldap_backend = settings.AUTH_BACKEND_LDAP
        backends = settings.AUTHENTICATION_BACKENDS
        has = ldap_backend in backends
        if setting.cleaned_value and not has:
            settings.AUTHENTICATION_BACKENDS.insert(0, ldap_backend)

        if not setting.cleaned_value and has:
            index = backends.index(ldap_backend)
            backends.pop(index)
        settings.AUTH_LDAP = setting.cleaned_value

    @classmethod
    def update_or_create(cls, name='', value='', encrypted=False, category=''):
        """
        不能使用 Model 提供的，update_or_create 因为这里有 encrypted 和 cleaned_value
        :return: (changed, instance)
        """
        setting = cls.objects.filter(name=name).first()
        changed = False
        if not setting:
            setting = Setting(name=name, encrypted=encrypted, category=category)
        if setting.cleaned_value != value:
            setting.encrypted = encrypted
            setting.cleaned_value = value
            setting.save()
            changed = True
        return changed, setting

    class Meta:
        db_table = "settings_setting"
        verbose_name = _("Setting")
