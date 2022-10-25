import yaml
import os.path
from rest_framework.exceptions import ValidationError

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel


__all__ = ['Applet', 'AppletPublication']


class Applet(JMSBaseModel):
    class Type(models.TextChoices):
        general = 'general', _('General')
        web = 'web', _('Web')

    class VCSType(models.TextChoices):
        manual = 'manual', _('Manual')
        git = 'git', _('Git')
        archive = 'archive', _('Remote gzip')

    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    version = models.CharField(max_length=16, verbose_name=_('Version'))
    author = models.CharField(max_length=128, verbose_name=_('Author'))
    path = models.FilePathField(verbose_name=_('Path'))
    type = models.CharField(max_length=16, verbose_name=_('Type'), default='general', choices=Type.choices)
    vcs_type = models.CharField(max_length=16, verbose_name=_('VCS type'), null=True)
    vcs_url = models.CharField(max_length=256, verbose_name=_('URL'), null=True)
    protocols = models.JSONField(default=list, verbose_name=_('Protocol'))
    tags = models.JSONField(default=list, verbose_name=_('Tags'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

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
        with open(path, 'rb') as f:
            return f.read()

    @classmethod
    def validate_manifest(cls, manifest):
        fields = ['name', 'display_name', 'version', 'author', 'type', 'tags', 'protocols']
        for field in fields:
            if field not in manifest:
                raise ValidationError(f'Missing field {field}')
        if manifest['type'] not in [i[0] for i in cls.Type.choices]:
            raise ValidationError('Invalid type')
        if not isinstance(manifest['protocols'], list):
            raise ValidationError('Invalid protocols')

    @classmethod
    def create_by_manifest(cls, manifest):
        obj = cls()
        for k, v in manifest.items():
            setattr(obj, k, v)
        obj.save()
        return obj


class AppletPublication(JMSBaseModel):
    applet = models.ForeignKey('Applet', on_delete=models.PROTECT, verbose_name=_('Applet'))
    host = models.ForeignKey('AppletHost', on_delete=models.PROTECT, verbose_name=_('Host'))
    status = models.CharField(max_length=16, verbose_name=_('Status'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        unique_together = ('applet', 'host')
