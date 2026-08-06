import os
import shutil
from collections import defaultdict

from django.core.files.storage import default_storage
from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.const import AllTypes, Category, Protocol, SuMethodChoices
from common.db.fields import JsonDictTextField
from common.db.models import JMSBaseModel

__all__ = ['Platform', 'PlatformPackage', 'PlatformProtocol', 'PlatformAutomation']

from common.utils import lazyproperty
from labels.mixins import LabeledMixin


class PlatformPackage(JMSBaseModel):
    """A persisted package that provides a Platform and its automations."""

    name = models.CharField(max_length=128, verbose_name=_("Name"))

    def __str__(self):
        return self.name

    @property
    def path(self):
        return default_storage.path(
            'platforms/packages/by-id/{}'.format(self.id)
        )

    @property
    def manifest_path(self):
        return os.path.join(self.path, 'platform.yml')

    @property
    def exists(self):
        return os.path.isfile(self.manifest_path)

    def persist(self, source_dir):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
        shutil.copytree(source_dir, self.path)
        return self.path

    def delete_files(self):
        if os.path.isdir(self.path):
            shutil.rmtree(self.path)

    @staticmethod
    def source_exists(source_dir):
        return os.path.isfile(os.path.join(source_dir, 'platform.yml'))

    @classmethod
    def load_manifest(cls, source_dir):
        from rest_framework.serializers import ValidationError
        from common.utils.yml import yaml_load_with_i18n

        path = os.path.join(source_dir, 'platform.yml')
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding='utf8') as stream:
                return yaml_load_with_i18n(stream)
        except Exception as error:
            raise ValidationError({
                'error': _("Load platform.yml failed: {}").format(error)
            })

    @classmethod
    def load_automation_methods(cls, source_dir, lang=None):
        from rest_framework.serializers import ValidationError
        from assets.automations.methods import (
            check_platform_method, check_platform_methods, generate_serializer,
        )
        from assets.utils.platform_package import is_ignored_pkg_path
        from common.utils.yml import yaml_load_with_i18n

        automations_dir = source_dir
        if os.path.basename(os.path.normpath(source_dir)) != 'automations':
            automations_dir = os.path.join(source_dir, 'automations')
        if not os.path.isdir(automations_dir):
            return []

        methods = []
        for action in os.listdir(automations_dir):
            if is_ignored_pkg_path(action):
                continue
            action_dir = os.path.join(automations_dir, action)
            if not os.path.isdir(action_dir):
                continue
            manifest_path = os.path.join(action_dir, 'manifest.yml')
            main_path = os.path.join(action_dir, 'main.yml')
            if not os.path.exists(manifest_path):
                raise ValidationError({
                    'error': _("Package automation missing manifest.yml: {}").format(action)
                })
            if not os.path.exists(main_path):
                raise ValidationError({
                    'error': _("Package automation missing main.yml: {}").format(action)
                })
            try:
                with open(manifest_path, encoding='utf8') as stream:
                    manifest = yaml_load_with_i18n(stream, lang=lang)
                check_platform_method(manifest, manifest_path)
            except ValueError as error:
                raise ValidationError({'error': str(error)})
            if manifest.get('method') != action:
                raise ValidationError({
                    'error': _(
                        "Package automation method does not match directory name: {}"
                    ).format(action)
                })
            manifest['dir'] = action_dir
            manifest['params_serializer'] = generate_serializer(manifest)
            methods.append(manifest)
        check_platform_methods(methods)
        return methods

    @classmethod
    def get_all_automation_methods(cls, lang=None, exclude_platform_name=None):
        from assets.automations.methods import check_platform_methods

        try:
            queryset = cls.objects.filter(
                platforms__category__in=[Category.CUSTOM, Category.WEB],
            )
            if exclude_platform_name:
                queryset = queryset.exclude(platforms__name=exclude_platform_name)
            packages = list(queryset.distinct())
        except Exception:
            # The model may be imported before migrations have been applied.
            return []

        methods = []
        for package in packages:
            if not package.exists:
                continue
            methods.extend(
                cls.load_automation_methods(package.path, lang=lang)
            )
        check_platform_methods(methods)
        return methods

    @classmethod
    def get_existing_automation_methods(cls, lang=None, exclude_platform_name=None):
        from accounts.automations import methods as account
        from assets.automations import methods as asset
        from assets.automations.methods import check_platform_methods

        methods = (
            asset.get_platform_automation_methods(asset.BASE_DIR, lang=lang)
            + account.get_platform_automation_methods(account.BASE_DIR, lang=lang)
            + cls.get_all_automation_methods(
                lang=lang, exclude_platform_name=exclude_platform_name
            )
        )
        check_platform_methods(methods)
        return methods

    @staticmethod
    def build_automation_defaults(methods):
        actions = (
            'ping', 'gather_facts', 'change_secret', 'push_account',
            'verify_account', 'gather_accounts', 'remove_account',
        )
        action_methods = defaultdict(list)
        for method in methods:
            action_methods[method['method']].append(method)

        defaults = {}
        for action in actions:
            methods_of_action = action_methods.get(action, [])
            defaults['{}_enabled'.format(action)] = bool(methods_of_action)
            if methods_of_action:
                methods_of_action = sorted(
                    methods_of_action, key=lambda item: item.get('priority', 10)
                )
                defaults['{}_method'.format(action)] = methods_of_action[0]['id']
        return defaults

    @classmethod
    def validate_automation_methods(cls, source_dir, platform_data=None):
        from rest_framework.serializers import ValidationError

        methods = cls.load_automation_methods(source_dir)
        if not platform_data:
            return methods
        category = platform_data.get('category')
        tp = platform_data.get('type')
        protocols = {
            item.get('name') for item in platform_data.get('protocols', [])
            if item.get('name')
        }
        for method in methods:
            categories = method.get('category') or []
            if isinstance(categories, str):
                categories = [categories]
            if category not in categories:
                raise ValidationError({
                    'error': _(
                        "Platform automation category must contain platform category: {}"
                    ).format(method['id'])
                })
            types = method.get('type') or []
            if 'all' not in types and tp not in types:
                raise ValidationError({
                    'error': _(
                        "Platform automation type must contain platform type: {}"
                    ).format(method['id'])
                })
            protocol = method.get('protocol')
            if protocol and protocols and protocol not in protocols:
                raise ValidationError({
                    'error': _(
                        "Platform automation protocol not found in platform.yml: {}"
                    ).format(method['id'])
                })
        return methods

    @classmethod
    def validate(cls, source_dir):
        from rest_framework.serializers import ValidationError

        data = cls.load_manifest(source_dir)
        if not data:
            return None
        methods = cls.validate_automation_methods(source_dir, data)
        existing = cls.get_existing_automation_methods(
            exclude_platform_name=data.get('name')
        )
        existing_ids = {item['id'] for item in existing}
        duplicate_ids = [item['id'] for item in methods if item['id'] in existing_ids]
        if duplicate_ids:
            raise ValidationError({
                'error': _("Platform automation method id already exists: {}").format(
                    ', '.join(sorted(set(duplicate_ids)))
                )
            })
        return data

    @classmethod
    def prepare_platform_data(cls, source_dir, data):
        from rest_framework.serializers import ValidationError

        if data['category'] not in [Category.CUSTOM, Category.WEB]:
            raise ValidationError({
                'error': _("Only support custom and web platform package")
            })
        try:
            tp = data['type']
        except KeyError:
            raise ValidationError({'error': _("Missing type in platform.yml")})
        methods = cls.validate_automation_methods(source_dir, data)
        automation = AllTypes.get_constraints(data['category'], tp).get('automation', {})
        if methods:
            automation = {
                **automation, 'ansible_enabled': True,
                **cls.build_automation_defaults(methods),
            }
        data = {
            **data,
            'automation': {**automation, **(data.get('automation') or {})},
        }
        return data, tp

    @classmethod
    def sync_platform(cls, source_dir, instance=None, created_by=''):
        from assets.models import PlatformAutomation
        from assets.serializers.platform import PlatformSerializer

        data = cls.load_manifest(source_dir)
        if not data:
            return None
        data, tp = cls.prepare_platform_data(source_dir, data)
        automation_data = data.get('automation') or {}
        serializer = PlatformSerializer(data=data, instance=instance)
        if tp not in serializer.fields['type'].choices:
            serializer.add_type_choices(tp, tp)
        serializer.is_valid(raise_exception=True)
        platform = serializer.save()
        automation = getattr(platform, 'automation', None)
        if automation is None:
            automation = PlatformAutomation.objects.create(platform=platform)
        for field, value in automation_data.items():
            setattr(automation, field, value)
        automation.save()
        if created_by:
            platform.created_by = created_by
            platform.save(update_fields=['created_by'])
        return platform

    class Meta:
        verbose_name = _("Platform package")


class PlatformProtocol(models.Model):
    name = models.CharField(max_length=32, verbose_name=_('Name'))
    port = models.IntegerField(verbose_name=_('Port'))
    primary = models.BooleanField(default=False, verbose_name=_('Primary'))
    required = models.BooleanField(default=False, verbose_name=_('Required'))
    default = models.BooleanField(default=False, verbose_name=_('Default'))
    public = models.BooleanField(default=True, verbose_name=_('Public'))
    setting = models.JSONField(verbose_name=_('Setting'), default=dict)
    platform = models.ForeignKey('Platform', on_delete=models.CASCADE, related_name='protocols')

    def __str__(self):
        return '{}/{}'.format(self.name, self.port)

    @property
    def secret_types(self) -> list:
        return Protocol.settings().get(self.name, {}).get('secret_types', ['password'])

    @lazyproperty
    def port_from_addr(self):
        from assets.const.protocol import Protocol as ProtocolConst
        return ProtocolConst.settings().get(self.name, {}).get('port_from_addr', False)


class PlatformAutomation(models.Model):
    ansible_enabled = models.BooleanField(default=False, verbose_name=_("Enabled"))
    ansible_config = models.JSONField(default=dict, verbose_name=_("Ansible config"))

    ping_enabled = models.BooleanField(default=False, verbose_name=_("Ping enabled"))
    ping_method = models.CharField(max_length=32, blank=True, null=True, verbose_name=_("Ping method"))
    ping_params = models.JSONField(default=dict, verbose_name=_("Ping params"))

    gather_facts_enabled = models.BooleanField(default=False, verbose_name=_("Gather facts enabled"))
    gather_facts_method = models.TextField(
        max_length=32, blank=True, null=True, verbose_name=_("Gather facts method")
    )
    gather_facts_params = models.JSONField(default=dict, verbose_name=_("Gather facts params"))

    change_secret_enabled = models.BooleanField(default=False, verbose_name=_("Change secret enabled"))
    change_secret_method = models.TextField(
        max_length=32, blank=True, null=True, verbose_name=_("Change secret method")
    )
    change_secret_params = models.JSONField(default=dict, verbose_name=_("Change secret params"))

    push_account_enabled = models.BooleanField(default=False, verbose_name=_("Push account enabled"))
    push_account_method = models.TextField(
        max_length=32, blank=True, null=True, verbose_name=_("Push account method")
    )
    push_account_params = models.JSONField(default=dict, verbose_name=_("Push account params"))

    verify_account_enabled = models.BooleanField(default=False, verbose_name=_("Verify account enabled"))
    verify_account_method = models.TextField(
        max_length=32, blank=True, null=True, verbose_name=_("Verify account method")
    )
    verify_account_params = models.JSONField(default=dict, verbose_name=_("Verify account params"))

    gather_accounts_enabled = models.BooleanField(default=False, verbose_name=_("Gather facts enabled"))
    gather_accounts_method = models.TextField(
        max_length=32, blank=True, null=True, verbose_name=_("Gather facts method")
    )
    gather_accounts_params = models.JSONField(default=dict, verbose_name=_("Gather facts params"))

    remove_account_enabled = models.BooleanField(default=False, verbose_name=_("Remove account enabled"))
    remove_account_method = models.TextField(
        max_length=32, blank=True, null=True, verbose_name=_("Remove account method")
    )
    remove_account_params = models.JSONField(default=dict, verbose_name=_("Remove account params"))
    platform = models.OneToOneField('Platform', on_delete=models.CASCADE, related_name='automation', null=True)


class Platform(LabeledMixin, JMSBaseModel):
    """
    对资产提供 约束和默认值
    对资产进行抽象
    """

    class CharsetChoices(models.TextChoices):
        utf8 = 'utf-8', 'UTF-8'
        gbk = 'gbk', 'GBK'

    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    name = models.SlugField(verbose_name=_("Name"), unique=True, allow_unicode=True)
    category = models.CharField(default='host', max_length=32, verbose_name=_("Category"))
    type = models.CharField(max_length=32, default='linux', verbose_name=_("Type"))
    meta = JsonDictTextField(blank=True, null=True, verbose_name=_("Meta"))
    internal = models.BooleanField(default=False, verbose_name=_("Internal"))
    package = models.ForeignKey(
        PlatformPackage, on_delete=models.SET_NULL, related_name='platforms',
        null=True, blank=True, verbose_name=_("Platform package")
    )
    # 资产有关的
    charset = models.CharField(
        default=CharsetChoices.utf8, choices=CharsetChoices.choices,
        max_length=8, verbose_name=_("Charset")
    )
    gateway_enabled = models.BooleanField(default=True, verbose_name=_("Gateway enabled"))
    ds_enabled = models.BooleanField(default=False, verbose_name=_("DS enabled"))
    # 账号有关的
    su_enabled = models.BooleanField(default=False, verbose_name=_("Su enabled"))
    su_method = models.CharField(max_length=32, blank=True, null=True, verbose_name=_("Su method"))
    custom_fields = models.JSONField(null=True, default=list, verbose_name=_("Custom fields"))

    @property
    def type_constraints(self):
        return AllTypes.get_constraints(self.category, self.type)

    @lazyproperty
    def assets_amount(self):
        return self.assets.count()

    def save(self, *args, **kwargs):
        if not self.ds_enabled:
            self.ds = None
        super().save(*args, **kwargs)

    @classmethod
    def default(cls):
        linux, created = cls.objects.get_or_create(
            defaults={'name': 'Linux'}, name='Linux'
        )
        return linux.id

    def is_huawei(self):
        if self.category != Category.DEVICE:
            return False
        if 'huawei' in self.name.lower():
            return True
        if '华为' in self.name:
            return True
        return False

    @property
    def ansible_become_method(self):
        su_method = self.su_method or SuMethodChoices.sudo
        if su_method in [SuMethodChoices.sudo, SuMethodChoices.only_sudo]:
            method = SuMethodChoices.sudo
        elif su_method in [SuMethodChoices.su, SuMethodChoices.only_su]:
            method = SuMethodChoices.su
        else:
            method = su_method
        return method

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Platform")
        # ordering = ('name',)
