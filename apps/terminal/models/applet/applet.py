import os.path
import random
import shutil
from collections import defaultdict

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
        community = 'community', _('Community edition')
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
    can_concurrent = models.BooleanField(default=False, verbose_name=_('Can concurrent'))
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

    host_prefer_key_tpl = 'applet_host_prefer_{}'

    @classmethod
    def clear_host_prefer(cls):
        cache.delete_pattern(cls.host_prefer_key_tpl.format('*'))

    def _select_by_load(self, hosts):
        using_keys = cache.keys(self.host_prefer_key_tpl.format('*'))
        using_host_ids = cache.get_many(using_keys)
        counts = defaultdict(int)
        for host_id in using_host_ids.values():
            counts[host_id] += 1

        hosts = list(sorted(hosts, key=lambda h: counts[str(h.id)]))
        return hosts[0] if hosts else None

    def select_host(self, user, asset):
        hosts = self.hosts.filter(is_active=True)
        hosts = [host for host in hosts if host.load != 'offline']
        if not hosts:
            return None

        spec_label = asset.labels.filter(label__name__in=['AppletHost', '发布机']).first()
        if spec_label and spec_label.label:
            label_value = spec_label.label.value
            matched = [host for host in hosts if host.name == label_value]
            if matched:
                return matched[0]

        hosts = [h for h in hosts if h.auto_create_accounts]
        prefer_key = self.host_prefer_key_tpl.format(user.id)
        prefer_host_id = cache.get(prefer_key, None)
        pref_host = [host for host in hosts if host.id == prefer_host_id]

        if pref_host:
            host = pref_host[0]
        else:
            host = self._select_by_load(hosts)
            if host is None:
                return
            cache.set(prefer_key, str(host.id), timeout=None)
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

    accounts_using_key_tmpl = 'applet_host_accounts_{}_{}_{}'

    def select_a_public_account(self, user, host, valid_accounts):
        using_keys = cache.keys(self.accounts_using_key_tmpl.format(host.id, '*', '*')) or []
        accounts_username_used = list(cache.get_many(using_keys).values())
        logger.debug('Applet host account using: {}: {}'.format(host.name, accounts_username_used))
        accounts = valid_accounts.exclude(username__in=accounts_username_used)
        public_accounts = accounts.filter(username__startswith='jms_')
        if not public_accounts:
            public_accounts = accounts \
                .exclude(username__in=['Administrator', 'root']) \
                .exclude(username__startswith='js_')
        account = self.random_select_prefer_account(user, host, public_accounts)
        return account

    def try_to_use_private_account(self, user, host, valid_accounts):
        host_can_concurrent = str(host.deploy_options.get('RDS_fSingleSessionPerUser', 0)) == '0'
        app_can_concurrent = self.can_concurrent or self.type == 'web'
        all_can_concurrent = host_can_concurrent and app_can_concurrent

        private_account = valid_accounts.filter(username='js_{}'.format(user.username)).first()
        if not private_account:
            logger.debug('Private account not found ...')
            return None
        # 优先使用 private account，支持并发或者不支持并发时，如果私有没有被占用，则使用私有
        account = None
        # 如果都支持，不管私有是否被占用，都使用私有
        if all_can_concurrent:
            logger.debug('All can concurrent, use private account')
            account = private_account
        # 如果主机都不支持并发，则查询一下私有账号有没有任何应用使用，如果没有被使用，则使用私有
        elif not host_can_concurrent:
            private_using_key = self.accounts_using_key_tmpl.format(host.id, private_account.username, '*')
            private_is_using = len(cache.keys(private_using_key))
            logger.debug("Private account is using: {}".format(private_is_using))
            if not private_is_using:
                account = private_account
        # 如果主机支持，但是应用不支持并发，则查询一下私有账号有没有被这个应用使用, 如果没有被使用，则使用私有
        elif host_can_concurrent and not app_can_concurrent:
            private_app_using_key = self.accounts_using_key_tmpl.format(host.id, private_account.username, self.name)
            private_is_using_by_this_app = cache.get(private_app_using_key, False)
            logger.debug("Private account is using {} by {}".format(private_is_using_by_this_app, self.name))
            if not private_is_using_by_this_app:
                account = private_account
        return account

    @staticmethod
    def try_to_use_same_account(user, host):
        from accounts.models import VirtualAccount

        if not host.using_same_account:
            return
        account = VirtualAccount.get_same_account(user, host)
        if not account.secret:
            return
        return account

    def select_host_account(self, user, asset):
        # 选择激活的发布机
        host = self.select_host(user, asset)
        if not host:
            return None
        logger.info('Select applet host: {}'.format(host.name))

        valid_accounts = host.accounts.all().filter(is_active=True, privileged=False)
        account = self.try_to_use_same_account(user, host)
        if not account:
            logger.debug('No same account, try to use private account')
            account = self.try_to_use_private_account(user, host, valid_accounts)

        if not account:
            logger.debug('No private account, try to use public account')
            account = self.select_a_public_account(user, host, valid_accounts)

        if not account:
            logger.debug('No available account for applet host: {}'.format(host.name))
            return None

        ttl = 60 * 60 * 24
        lock_key = self.accounts_using_key_tmpl.format(host.id, account.username, self.name)
        cache.set(lock_key, account.username, ttl)

        res = {
            'host': host,
            'account': account,
            'lock_key': lock_key
        }
        logger.debug('Select host and account: {}-{}'.format(host.name, account.username))
        return res

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
