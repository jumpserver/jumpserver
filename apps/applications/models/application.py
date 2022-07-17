from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgModelMixin
from common.mixins import CommonModelMixin
from common.utils import is_uuid
from assets.models import Asset

from .. import const
from .tree import ApplicationTreeNodeMixin


class Application(CommonModelMixin, OrgModelMixin, ApplicationTreeNodeMixin):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    category = models.CharField(
        max_length=16, choices=const.AppCategory.choices, verbose_name=_('Category')
    )
    type = models.CharField(
        max_length=16, choices=const.AppType.choices, verbose_name=_('Type')
    )
    domain = models.ForeignKey(
        'assets.Domain', null=True, blank=True, related_name='applications',
        on_delete=models.SET_NULL, verbose_name=_("Domain"),
    )
    attrs = models.JSONField(default=dict, verbose_name=_('Attrs'))
    comment = models.TextField(
        max_length=128, default='', blank=True, verbose_name=_('Comment')
    )

    class Meta:
        verbose_name = _('Application')
        unique_together = [('org_id', 'name')]
        ordering = ('name',)
        permissions = [
            ('match_application', _('Can match application')),
        ]

    def __str__(self):
        category_display = self.get_category_display()
        type_display = self.get_type_display()
        return f'{self.name}({type_display})[{category_display}]'

    @property
    def category_remote_app(self):
        return self.category == const.AppCategory.remote_app.value

    @property
    def category_cloud(self):
        return self.category == const.AppCategory.cloud.value

    @property
    def category_db(self):
        return self.category == const.AppCategory.db.value

    def get_rdp_remote_app_setting(self):
        from applications.serializers.attrs import get_serializer_class_by_application_type
        if not self.category_remote_app:
            raise ValueError(f"Not a remote app application: {self.name}")
        serializer_class = get_serializer_class_by_application_type(self.type)
        fields = serializer_class().get_fields()

        parameters = [self.type]
        for field_name in list(fields.keys()):
            if field_name in ['asset']:
                continue
            value = self.attrs.get(field_name)
            if not value:
                continue
            if field_name == 'path':
                value = '\"%s\"' % value
            parameters.append(str(value))

        parameters = ' '.join(parameters)
        return {
            'program': '||jmservisor',
            'working_directory': '',
            'parameters': parameters
        }

    def get_remote_app_asset(self, raise_exception=True):
        asset_id = self.attrs.get('asset')
        if is_uuid(asset_id):
            return Asset.objects.filter(id=asset_id).first()
        if raise_exception:
            raise ValueError("Remote App not has asset attr")

    def get_target_ip(self):
        target_ip = ''
        if self.category_remote_app:
            asset = self.get_remote_app_asset()
            target_ip = asset.ip if asset else target_ip
        elif self.category_cloud:
            target_ip = self.attrs.get('cluster')
        elif self.category_db:
            target_ip = self.attrs.get('host')
        return target_ip

