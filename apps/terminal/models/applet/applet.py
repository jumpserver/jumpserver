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

from assets.models import Platform, PlatformPackage
from assets.utils.platform_package import (
    locate_package_root,
)
from common.db.models import JMSBaseModel
from common.utils import lazyproperty, get_logger
from common.utils.yml import yaml_load_with_i18n
from terminal.const import PublishStatus
from terminal.utils.tinker import get_tinker_version_status

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
    def path(self) -> str:
        if self.builtin:
            return os.path.join(settings.APPS_DIR, 'terminal', 'applets', self.name)
        else:
            return default_storage.path('applets/{}'.format(self.name))

    @lazyproperty
    def readme(self) -> str:
        readme_file = os.path.join(self.path, 'README.md')
        if os.path.isfile(readme_file):
            with open(readme_file, 'r') as f:
                return f.read()
        return ''

    @property
    def manifest(self) -> dict:
        path = os.path.join(self.path, 'manifest.yml')
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return yaml.safe_load(f)
        
    @lazyproperty
    def platform_manifest(self) -> dict:
        path = os.path.join(self.path, 'platform.yml')
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    @property
    def icon(self) -> str:
        path = os.path.join(self.path, 'icon.png')
        if not os.path.exists(path):
            return None
        return os.path.join(settings.MEDIA_URL, 'applets', self.name, 'icon.png')

    @classmethod
    def validate_pkg(cls, d):
        files = ['manifest.yml', 'icon.png', 'setup.yml']
        for name in files:
            path = os.path.join(d, name)
            if not os.path.exists(path):
                raise ValidationError({'error': _('Applet pkg not valid, Missing file {}').format(name)})

        with open(os.path.join(d, 'manifest.yml'), encoding='utf8') as f:
            manifest = yaml_load_with_i18n(f)

        if not manifest.get('name', ''):
            raise ValidationError({'error': 'Missing name in manifest.yml'})
        has_platform = PlatformPackage.source_exists(d)
        methods = PlatformPackage.load_automation_methods(d)
        if methods and not has_platform:
            raise ValidationError({
                'error': _('Applet automation requires platform.yml')
            })
        if has_platform:
            PlatformPackage.validate(d)
        return manifest

    @staticmethod
    def locate_pkg_root(extract_to, filename):
        return locate_package_root(extract_to, filename, 'manifest.yml')

    def load_platform_if_need(self, d):
        if not PlatformPackage.source_exists(d):
            return
        created_by = 'Applet:{}'.format(self.name)
        instance = self.get_related_platform()
        platform = PlatformPackage.sync_platform(
            d, instance=instance, created_by=created_by
        )

        # Applet is only the delivery vehicle. Once it contains automation,
        # persist it as a PlatformPackage and load methods from that package.
        methods = PlatformPackage.load_automation_methods(d)
        package = platform.package
        if not methods and package is None:
            return platform
        if package is None:
            package = PlatformPackage.objects.create(name=platform.name)
            platform.package = package
            platform.save(update_fields=['package'])
        package.persist(d)
        return platform

    @classmethod
    def install_from_dir(cls, path, builtin=True):
        from assets.const import AllTypes
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
        AllTypes.reload_automation_methods()
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

    def _filter_published_hosts(self, hosts):
        if settings.DEBUG_DEV:
            return True
        exclude_status = [PublishStatus.pending, PublishStatus.failed]
        publications = (
            AppletPublication.objects
            .filter(applet=self, host__in=hosts)
            .exclude(status__in=exclude_status)
        )
        if not publications:
            return None
        return [p.host for p in publications]

    def filter_available_hosts(self):
        hosts = self.hosts.filter(is_active=True)

        if not hosts:
            logger.info("No active host for applet: {}".format(self.name))
            return None

        if settings.DEBUG_DEV:
            return hosts

        hosts = self._filter_published_hosts(hosts)
        if not hosts:
            logger.info("No published host for applet: {}".format(self.name))
            return None
        return hosts

    def select_host(self, user, asset):
        hosts = self.filter_available_hosts()
        hosts = [h for h in (hosts or [])
                 if get_tinker_version_status(h.tinker_version) not in ('unknown', 'unsupported')]
        if not hosts:
            return None

        only_label_values = asset.get_labels().filter(
            name__in=['AppletHostOnly', '仅发布机']
        ).values_list('value', flat=True)
        if only_label_values:
            host_matched = [host for host in hosts if host.name in only_label_values]
            if host_matched:
                return host_matched[0]
            else:
                logger.info("No host for only applet: {}".format(self.name))
                return None

        hosts = hosts if settings.DEBUG_DEV else [host for host in hosts if host.load != 'offline']
        if not hosts:
            logger.info("No online host for applet: {}".format(self.name))
            return None

        spec_label_values = asset.get_labels().filter(
            name__in=['AppletHost', '发布机']
        ).values_list('value', flat=True)
        host_matched = [host for host in hosts if host.name in spec_label_values]
        if host_matched:
            return random.choice(host_matched)

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
        verbose_name = _("Applet Publication")
