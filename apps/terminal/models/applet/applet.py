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

from common.db.models import JMSBaseModel
from common.utils import lazyproperty, get_logger
from jumpserver.utils import has_valid_xpack_license

logger = get_logger(__name__)

__all__ = ['Applet', 'AppletPublication']


class Applet(JMSBaseModel):
    class Type(models.TextChoices):
        general = 'general', _('General')
        web = 'web', _('Web')

    name = models.SlugField(max_length=128, verbose_name=_('Name'), unique=True)
    display_name = models.CharField(max_length=128, verbose_name=_('Display name'))
    version = models.CharField(max_length=16, verbose_name=_('Version'))
    author = models.CharField(max_length=128, verbose_name=_('Author'))
    type = models.CharField(max_length=16, verbose_name=_('Type'), default='general', choices=Type.choices)
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    builtin = models.BooleanField(default=False, verbose_name=_('Builtin'))
    protocols = models.JSONField(default=list, verbose_name=_('Protocol'))
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
        files = ['manifest.yml', 'icon.png', 'i18n.yml', 'setup.yml']
        for name in files:
            path = os.path.join(d, name)
            if not os.path.exists(path):
                raise ValidationError({'error': _('Applet pkg not valid, Missing file {}').format(name)})

        with open(os.path.join(d, 'manifest.yml')) as f:
            manifest = yaml.safe_load(f)

        if not manifest.get('name', ''):
            raise ValidationError({'error': 'Missing name in manifest.yml'})
        return manifest

    @classmethod
    def install_from_dir(cls, path):
        from terminal.serializers import AppletSerializer

        manifest = cls.validate_pkg(path)
        name = manifest['name']
        if not has_valid_xpack_license() and name.lower() in ('navicat', ):
            return

        instance = cls.objects.filter(name=name).first()
        serializer = AppletSerializer(instance=instance, data=manifest)
        serializer.is_valid()
        serializer.save(builtin=True)
        pkg_path = default_storage.path('applets/{}'.format(name))

        if os.path.exists(pkg_path):
            shutil.rmtree(pkg_path)
        shutil.copytree(path, pkg_path)
        return instance

    def select_host_account(self):
        # 选择激活的发布机
        hosts = list(self.hosts.filter(is_active=True).all())
        if not hosts:
            return None

        key_tmpl = 'applet_host_accounts_{}_{}'
        host = random.choice(hosts)
        using_keys = cache.keys(key_tmpl.format(host.id, '*')) or []
        accounts_username_used = list(cache.get_many(using_keys).values())
        logger.debug('Applet host account using: {}: {}'.format(host.name, accounts_username_used))
        accounts = host.accounts.all() \
            .filter(is_active=True, privileged=False) \
            .exclude(username__in=accounts_username_used)

        msg = 'Applet host remain accounts: {}: {}'.format(host.name, len(accounts))
        if len(accounts) == 0:
            logger.error(msg)
        else:
            logger.debug(msg)

        if not accounts:
            return None

        account = random.choice(accounts)
        ttl = 60 * 60 * 24
        lock_key = key_tmpl.format(host.id, account.username)
        cache.set(lock_key, account.username, ttl)

        return {
            'host': host,
            'account': account,
            'lock_key': lock_key,
            'ttl': ttl
        }


class AppletPublication(JMSBaseModel):
    applet = models.ForeignKey('Applet', on_delete=models.CASCADE, related_name='publications',
                               verbose_name=_('Applet'))
    host = models.ForeignKey('AppletHost', on_delete=models.CASCADE, related_name='publications',
                             verbose_name=_('Hosting'))
    status = models.CharField(max_length=16, default='pending', verbose_name=_('Status'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        unique_together = ('applet', 'host')
