import os.path
import random
import shutil

import yaml
from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import ValidationError

from assets.models import Platform
from common.db.models import JMSBaseModel
from common.utils import lazyproperty, get_logger
from common.utils.yml import yaml_load_with_i18n

logger = get_logger(__name__)

__all__ = ['Applet', 'AppletPublication']


class Applet(JMSBaseModel):
    class Type(models.TextChoices):
        general = 'general', _('General')
        web = 'web', _('Web')

    class Edition(models.TextChoices):
        community = 'community', _('Community')
        enterprise = 'enterprise', _('Enterprise')

    name = models.SlugField(max_length=128, verbose_name=_('Name'), unique=True)
    display_name = models.CharField(max_length=128, verbose_name=_('Display name'))
    version = models.CharField(max_length=16, verbose_name=_('Version'))
    author = models.CharField(max_length=128, verbose_name=_('Author'))
    edition = models.CharField(max_length=128, choices=Edition.choices, default=Edition.community,
                               verbose_name=_('Edition'))
    type = models.CharField(max_length=16, verbose_name=_('Type'), default='general', choices=Type.choices)
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    builtin = models.BooleanField(default=False, verbose_name=_('Builtin'))
    protocols = models.JSONField(default=list, verbose_name=_('Protocol'))
    can_concurrent = models.BooleanField(default=True, verbose_name=_('Can concurrent'))
    tags = models.JSONField(default=list, verbose_name=_('Tags'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    hosts = models.ManyToManyField(
        through_fields=('applet', 'host'), through='AppletPublication',
        to='AppletHost', verbose_name=_('Hosts')
    )

    class Meta:
        verbose_name = _("Applet")

    def __str__(self):
        return self.name

    @property
    def path(self):
        if self.builtin:
            return os.path.join(settings.APPS_DIR, 'terminal', 'applets', self.name)
        else:
            return default_storage.path('applets/{}'.format(self.name))

    @lazyproperty
    def readme(self):
        readme_file = os.path.join(self.path, 'README.md')
        if os.path.isfile(readme_file):
            with open(readme_file, 'r') as f:
                return f.read()
        return ''

    @property
    def manifest(self):
        path = os.path.join(self.path, 'manifest.yml')
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    @property
    def icon(self):
        path = os.path.join(self.path, 'icon.png')
        if not os.path.exists(path):
            return None
        return os.path.join(settings.MEDIA_URL, 'applets', self.name, 'icon.png')

    @staticmethod
    def validate_pkg(d):
        files = ['manifest.yml', 'icon.png', 'setup.yml']
        for name in files:
            path = os.path.join(d, name)
            if not os.path.exists(path):
                raise ValidationError({'error': _('Applet pkg not valid, Missing file {}').format(name)})

        with open(os.path.join(d, 'manifest.yml'), encoding='utf8') as f:
            manifest = yaml_load_with_i18n(f)

        if not manifest.get('name', ''):
            raise ValidationError({'error': 'Missing name in manifest.yml'})
        return manifest

    def load_platform_if_need(self, d):
        from assets.serializers import PlatformSerializer
        from assets.const import CustomTypes

        if not os.path.exists(os.path.join(d, 'platform.yml')):
            return
        try:
            with open(os.path.join(d, 'platform.yml'), encoding='utf8') as f:
                data = yaml_load_with_i18n(f)
        except Exception as e:
            raise ValidationError({'error': _('Load platform.yml failed: {}').format(e)})

        if data['category'] != 'custom':
            raise ValidationError({'error': _('Only support custom platform')})

        try:
            tp = data['type']
        except KeyError:
            raise ValidationError({'error': _('Missing type in platform.yml')})

        if not data.get('automation'):
            data['automation'] = CustomTypes._get_automation_constrains()['*']

        created_by = 'Applet:{}'.format(self.name)
        instance = self.get_related_platform()
        s = PlatformSerializer(data=data, instance=instance)
        s.add_type_choices(tp, tp)
        s.is_valid(raise_exception=True)
        p = s.save()
        p.created_by = created_by
        p.save(update_fields=['created_by'])

    @classmethod
    def install_from_dir(cls, path, builtin=True):
        from terminal.serializers import AppletSerializer

        manifest = cls.validate_pkg(path)
        name = manifest['name']
        instance = cls.objects.filter(name=name).first()
        serializer = AppletSerializer(instance=instance, data=manifest)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(builtin=builtin)
        instance.load_platform_if_need(path)

        pkg_path = default_storage.path('applets/{}'.format(name))
        if os.path.exists(pkg_path):
            shutil.rmtree(pkg_path)
        shutil.copytree(path, pkg_path)
        return instance, serializer

    def select_host(self, user):
        hosts = [
            host for host in self.hosts.filter(is_active=True)
            if host.load != 'offline'
        ]
        if not hosts:
            return None

        prefer_key = 'applet_host_prefer_{}'.format(user.id)
        prefer_host_id = cache.get(prefer_key, None)
        pref_host = [host for host in hosts if host.id == prefer_host_id]
        if pref_host:
            host = pref_host[0]
        else:
            host = random.choice(hosts)
            cache.set(prefer_key, host.id, timeout=None)
        return host

    def get_related_platform(self):
        created_by = 'Applet:{}'.format(self.name)
        platform = Platform.objects.filter(created_by=created_by).first()
        return platform

    @staticmethod
    def random_select_prefer_account(user, host, accounts):
        msg = 'Applet host remain public accounts: {}: {}'.format(host.name, len(accounts))
        if len(accounts) == 0:
            logger.error(msg)
            return None
        prefer_host_account_key = 'applet_host_prefer_account_{}_{}'.format(user.id, host.id)
        prefer_account_id = cache.get(prefer_host_account_key, None)
        prefer_account = None
        if prefer_account_id:
            prefer_account = accounts.filter(id=prefer_account_id).first()
        if prefer_account:
            account = prefer_account
        else:
            account = random.choice(accounts)
            cache.set(prefer_host_account_key, account.id, timeout=None)
        return account

    def select_host_account(self, user):
        # 选择激活的发布机
        host = self.select_host(user)
        if not host:
            return None
        host_concurrent = str(host.deploy_options.get('RDS_fSingleSessionPerUser', 0)) == '0'
        can_concurrent = (self.can_concurrent or self.type == 'web') and host_concurrent

        accounts = host.accounts.all().filter(is_active=True, privileged=False)
        private_account = accounts.filter(username='js_{}'.format(user.username)).first()
        accounts_using_key_tmpl = 'applet_host_accounts_{}_{}'

        if private_account and can_concurrent:
            account = private_account
        else:
            using_keys = cache.keys(accounts_using_key_tmpl.format(host.id, '*')) or []
            accounts_username_used = list(cache.get_many(using_keys).values())
            logger.debug('Applet host account using: {}: {}'.format(host.name, accounts_username_used))

            # 优先使用 private account
            if private_account and private_account.username not in accounts_username_used:
                account = private_account
            else:
                accounts = accounts.exclude(username__in=accounts_username_used) \
                    .filter(username__startswith='jms_')
                account = self.random_select_prefer_account(user, host, accounts)
                if not account:
                    return
        ttl = 60 * 60 * 24
        lock_key = accounts_using_key_tmpl.format(host.id, account.username)
        cache.set(lock_key, account.username, ttl)

        return {
            'host': host,
            'account': account,
            'lock_key': lock_key,
            'ttl': ttl
        }

    def delete(self, using=None, keep_parents=False):
        platform = self.get_related_platform()
        if platform and platform.assets.count() == 0:
            platform.delete()
        return super().delete(using, keep_parents)


class AppletPublication(JMSBaseModel):
    applet = models.ForeignKey('Applet', on_delete=models.CASCADE, related_name='publications',
                               verbose_name=_('Applet'))
    host = models.ForeignKey('AppletHost', on_delete=models.CASCADE, related_name='publications',
                             verbose_name=_('Hosting'))
    status = models.CharField(max_length=16, default='pending', verbose_name=_('Status'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        unique_together = ('applet', 'host')
