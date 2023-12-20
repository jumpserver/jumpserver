import json

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.db.utils import ProgrammingError, OperationalError
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
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
    value = models.TextField(verbose_name=_("Value"), null=True, blank=True)
    category = models.CharField(max_length=128, default="default", verbose_name=_('Category'))
    encrypted = models.BooleanField(default=False, verbose_name=_('Encrypted'))
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True)
    comment = models.TextField(verbose_name=_("Comment"))

    objects = SettingManager()
    cache_key_prefix = '_SETTING_'

    def __str__(self):
        return self.name

    def is_name(self, name):
        return self.name == name

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
        setattr(settings, self.name, self.cleaned_value)
        self.refresh_keycloak_to_openid_if_need()

    def refresh_keycloak_to_openid_if_need(self):
        watch_config_names = [
            'AUTH_OPENID', 'AUTH_OPENID_REALM_NAME', 'AUTH_OPENID_SERVER_URL',
            'AUTH_OPENID_PROVIDER_ENDPOINT', 'AUTH_OPENID_KEYCLOAK'
        ]
        if self.name not in watch_config_names:
            # 不在监听的配置中, 不需要刷新
            return
        auth_keycloak = self.__class__.objects.filter(name='AUTH_OPENID_KEYCLOAK').first()
        if not auth_keycloak or not auth_keycloak.cleaned_value:
            # 关闭 Keycloak 方式的配置, 不需要刷新
            return

        from jumpserver.conf import Config
        config_names = [
            'AUTH_OPENID', 'AUTH_OPENID_REALM_NAME',
            'AUTH_OPENID_SERVER_URL', 'AUTH_OPENID_PROVIDER_ENDPOINT'
        ]
        # 获取当前 keycloak 配置
        keycloak_config = {}
        for name in config_names:
            setting = self.__class__.objects.filter(name=name).first()
            if not setting:
                continue
            value = setting.cleaned_value
            keycloak_config[name] = value

        # 转化 keycloak 配置为 openid 配置
        openid_config = Config.convert_keycloak_to_openid(keycloak_config)
        if not openid_config:
            return
        # 刷新 settings
        for key, value in openid_config.items():
            setattr(settings, key, value)
            self.__class__.update_or_create(key, value, encrypted=False, category=self.category)

    @classmethod
    def save_to_file(cls, value: InMemoryUploadedFile):
        filename = value.name
        filepath = f'settings/{filename}'
        path = default_storage.save(filepath, ContentFile(value.read()))
        url = default_storage.url(path)
        return url

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

        if isinstance(value, InMemoryUploadedFile):
            value = cls.save_to_file(value)

        if setting.cleaned_value != value:
            setting.encrypted = encrypted
            setting.cleaned_value = value
            setting.save()
            changed = True
        return changed, setting

    class Meta:
        db_table = "settings_setting"
        verbose_name = _("System setting")
        permissions = [
            ('change_email', _('Can change email setting')),
            ('change_auth', _('Can change auth setting')),
            ('change_ops', _('Can change auth ops')),
            ('change_ticket', _('Can change auth ticket')),
            ('change_virtualapp', _('Can change virtual app setting')),
            ('change_announcement', _('Can change auth announcement')),
            ('change_vault', _('Can change vault setting')),
            ('change_chatai', _('Can change chat ai setting')),
            ('change_systemmsgsubscription', _('Can change system msg sub setting')),
            ('change_sms', _('Can change sms setting')),
            ('change_security', _('Can change security setting')),
            ('change_clean', _('Can change clean setting')),
            ('change_interface', _('Can change interface setting')),
            ('change_license', _('Can change license setting')),
            ('change_terminal', _('Can change terminal setting')),
            ('change_other', _('Can change other setting')),
        ]


class ChatPrompt(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    content = models.TextField(blank=False, null=False, verbose_name=_('Content'))
    builtin = models.BooleanField(default=False, verbose_name=_('Builtin'))

    class Meta:
        verbose_name = _("Chat prompt")

    def __str__(self):
        return self.name
