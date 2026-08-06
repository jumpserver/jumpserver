import os
import shutil

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db import models
from django.utils._os import safe_join
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import ValidationError

from assets.utils.platform_package import locate_package_root
from common.db.models import JMSBaseModel
from common.utils import lazyproperty
from common.utils import get_logger
from common.utils.yml import yaml_load_with_i18n
from terminal.const import ComponentLoad, PublishStatus

__all__ = ['VirtualApp', 'VirtualAppPublication']

logger = get_logger(__name__)


class VirtualApp(JMSBaseModel):
    name = models.SlugField(max_length=128, verbose_name=_('Name'), unique=True)
    display_name = models.CharField(max_length=128, verbose_name=_('Display name'))
    version = models.CharField(max_length=16, verbose_name=_('Version'))
    author = models.CharField(max_length=128, verbose_name=_('Author'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    protocols = models.JSONField(default=list, verbose_name=_('Protocol'))
    image_name = models.CharField(max_length=128, verbose_name=_('Image name'))
    image_protocol = models.CharField(max_length=16, default='vnc', verbose_name=_('Image protocol'))
    image_port = models.IntegerField(default=5900, verbose_name=_('Image port'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    tags = models.JSONField(default=list, verbose_name=_('Tags'))
    providers = models.ManyToManyField(
        through_fields=('app', 'provider',), through='VirtualAppPublication',
        to='AppProvider', verbose_name=_('Providers')
    )

    provider_prefer_key_tpl = 'virtual_app_provider_prefer_{}_{}'

    class Meta:
        verbose_name = _('Virtual app')

    def __str__(self):
        return self.name

    @property
    def path(self):
        return default_storage.path('virtual_apps/{}'.format(self.name))

    @lazyproperty
    def readme(self) -> str:
        readme_file = os.path.join(self.path, 'README.md')
        if os.path.isfile(readme_file):
            with open(readme_file, 'r') as f:
                return f.read()
        return ''

    @property
    def icon(self) -> str:
        path = os.path.join(self.path, 'icon.png')
        if not os.path.exists(path):
            return None
        return os.path.join(settings.MEDIA_URL, 'virtual_apps', self.name, 'icon.png')

    @staticmethod
    def validate_pkg(d):
        files = ['manifest.yml', 'icon.png', ]
        for name in files:
            path = safe_join(d, name)
            if not os.path.exists(path):
                raise ValidationError({'error': _('Applet pkg not valid, Missing file {}').format(name)})

        with open(safe_join(d, 'manifest.yml'), encoding='utf8') as f:
            manifest = yaml_load_with_i18n(f)

        if not manifest.get('name', ''):
            raise ValidationError({'error': 'Missing name in manifest.yml'})
        return manifest

    @staticmethod
    def locate_pkg_root(extract_to, filename):
        return locate_package_root(extract_to, filename, 'manifest.yml')

    @classmethod
    def install_from_dir(cls, path):
        from terminal.serializers import VirtualAppSerializer
        manifest = cls.validate_pkg(path)
        name = manifest['name']
        instance = cls.objects.filter(name=name).first()
        serializer = VirtualAppSerializer(instance=instance, data=manifest)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        pkg_path = default_storage.path('virtual_apps/{}'.format(name))
        if os.path.exists(pkg_path):
            shutil.rmtree(pkg_path)
        shutil.copytree(path, pkg_path)
        return instance, serializer

    def filter_available_providers(self):
        """Return providers where this app has been published successfully.

        A provider without a bound terminal, or whose terminal reports offline,
        must not receive a new virtual application instance.
        """
        publications = self.publications.filter(
            status=PublishStatus.success
        ).select_related('provider__terminal')
        providers = [
            publication.provider for publication in publications
            if publication.provider.load != ComponentLoad.offline
            and publication.provider.connection_ready
        ]
        if not providers:
            logger.info('No available provider for virtual app: %s', self.name)
        return providers

    @classmethod
    def clear_provider_prefer(cls):
        cache.delete_pattern(cls.provider_prefer_key_tpl.format('*', '*'))

    @classmethod
    def _select_provider_by_load(cls, providers):
        load_priorities = {
            ComponentLoad.normal: 0,
            ComponentLoad.high: 1,
            ComponentLoad.critical: 2,
        }
        return min(
            providers,
            key=lambda provider: (
                load_priorities.get(provider.load, 3),
                provider.container_count,
                str(provider.id),
            ),
            default=None,
        )

    def select_provider(self, user):
        providers = self.filter_available_providers()
        if not providers:
            return None

        prefer_key = self.provider_prefer_key_tpl.format(self.id, user.id)
        preferred_provider_id = cache.get(prefer_key)
        preferred_provider = next(
            (item for item in providers if str(item.id) == str(preferred_provider_id)),
            None,
        )
        provider = self._select_provider_by_load(providers)
        # Affinity may choose a busier provider, but must never override a
        # healthier load class.
        if preferred_provider and preferred_provider.load == provider.load:
            provider = preferred_provider
        elif provider:
            cache.set(prefer_key, str(provider.id), timeout=None)
        return provider


class VirtualAppPublication(JMSBaseModel):
    provider = models.ForeignKey(
        'AppProvider', on_delete=models.CASCADE, related_name='publications', verbose_name=_('App Provider')
    )
    app = models.ForeignKey(
        'VirtualApp', on_delete=models.CASCADE, related_name='publications', verbose_name=_('Virtual app')
    )
    status = models.CharField(max_length=16, default='pending', verbose_name=_('Status'))
    app_version = models.CharField(
        max_length=16, blank=True, default='', verbose_name=_('Published version')
    )
    image_digest = models.CharField(
        max_length=255, blank=True, default='', verbose_name=_('Image digest')
    )
    date_synced = models.DateTimeField(
        null=True, blank=True, verbose_name=_('Date synced')
    )

    class Meta:
        verbose_name = _('Virtual app publication')
        unique_together = ('provider', 'app')
