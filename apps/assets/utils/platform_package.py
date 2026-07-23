import os
import re
import shutil
from collections import defaultdict

from django.core.files.storage import default_storage
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import ValidationError

from assets.automations.methods import get_platform_automation_methods, check_platform_methods
from assets.const import AllTypes, Category
from common.utils.yml import yaml_load_with_i18n

AUTOMATION_ACTION_FIELDS = (
    'ping',
    'gather_facts',
    'change_secret',
    'push_account',
    'verify_account',
    'gather_accounts',
    'remove_account',
)


def is_ignored_pkg_path(path):
    parts = os.path.normpath(path).split(os.sep)
    for part in parts:
        if not part:
            continue
        if part == '__MACOSX' or part.startswith('._'):
            return True
    return False


def get_platform_package_path(pkg_dir):
    return os.path.join(pkg_dir, 'platform.yml')


def get_persisted_platform_package_dir(platform_name):
    return default_storage.path('platforms/packages/{}'.format(platform_name))


def has_platform_package(pkg_dir):
    return os.path.exists(get_platform_package_path(pkg_dir))


def locate_package_root(extract_to, filename, required_file):
    candidates = []

    expected = os.path.join(extract_to, filename.replace('.zip', ''))
    if os.path.exists(expected):
        candidates.append(expected)

    matched = re.match(r"(\w+)", filename)
    if matched:
        expected_by_name = os.path.join(extract_to, matched.group())
        if os.path.exists(expected_by_name):
            candidates.append(expected_by_name)

    for item in os.listdir(extract_to):
        if is_ignored_pkg_path(item):
            continue
        path = os.path.join(extract_to, item)
        if not os.path.isdir(path):
            continue
        if os.path.exists(os.path.join(path, required_file)):
            candidates.append(path)

    unique_candidates = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)

    if len(unique_candidates) == 1:
        return unique_candidates[0]
    if unique_candidates:
        return unique_candidates[0]
    return expected


def load_platform_package_data(pkg_dir):
    path = get_platform_package_path(pkg_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf8') as f:
            return yaml_load_with_i18n(f)
    except Exception as e:
        raise ValidationError({'error': _('Load platform.yml failed: {}').format(e)})


def get_platform_automation_methods_from_pkg(pkg_dir, lang=None):
    automations_dir = os.path.join(pkg_dir, 'automations')
    if not os.path.isdir(automations_dir):
        return []
    return get_platform_automation_methods(automations_dir, lang=lang)


def get_persisted_platform_automation_methods(lang=None, exclude_platform_name=None):
    from assets.models import Platform

    methods = []
    try:
        platforms = Platform.objects.filter(category__in=[Category.CUSTOM, Category.WEB]).only('name')
    except Exception:
        return methods

    for platform in platforms:
        if exclude_platform_name and platform.name == exclude_platform_name:
            continue
        pkg_dir = get_persisted_platform_package_dir(platform.name)
        if not os.path.isdir(pkg_dir):
            continue
        methods.extend(get_platform_automation_methods_from_pkg(pkg_dir, lang=lang))

    check_platform_methods(methods)
    return methods


def get_existing_platform_automation_methods(lang=None, exclude_platform_name=None):
    from assets.automations import methods as asset
    from accounts.automations import methods as account
    from terminal.models import Applet

    methods = (
        asset.get_platform_automation_methods(asset.BASE_DIR, lang=lang)
        + account.get_platform_automation_methods(account.BASE_DIR, lang=lang)
        + get_persisted_platform_automation_methods(
            lang=lang, exclude_platform_name=exclude_platform_name
        )
        + Applet.get_automation_methods(lang=lang)
    )
    check_platform_methods(methods)
    return methods


def build_platform_automation_defaults(methods):
    defaults = {}
    action_methods = defaultdict(list)
    for method in methods:
        action_methods[method['method']].append(method)

    for action in AUTOMATION_ACTION_FIELDS:
        enabled_key = f'{action}_enabled'
        method_key = f'{action}_method'
        methods_of_action = action_methods.get(action, [])
        defaults[enabled_key] = bool(methods_of_action)
        if methods_of_action:
            methods_of_action = sorted(methods_of_action, key=lambda item: item.get('priority', 10))
            defaults[method_key] = methods_of_action[0]['id']
    return defaults


def validate_platform_automation_methods(pkg_dir, platform_data=None):
    methods = get_platform_automation_methods_from_pkg(pkg_dir)
    if not platform_data:
        return methods

    category = platform_data.get('category')
    tp = platform_data.get('type')
    protocols = {
        item.get('name') for item in platform_data.get('protocols', [])
        if item.get('name')
    }

    for method in methods:
        method_categories = method.get('category') or []
        if isinstance(method_categories, str):
            method_categories = [method_categories]
        if category not in method_categories:
            raise ValidationError({
                'error': _('Platform automation category must contain platform category: {}').format(method['id'])
            })

        method_types = method.get('type') or []
        if 'all' not in method_types and tp not in method_types:
            raise ValidationError({
                'error': _('Platform automation type must contain platform type: {}').format(method['id'])
            })

        protocol = method.get('protocol')
        if protocol and protocols and protocol not in protocols:
            raise ValidationError({
                'error': _('Platform automation protocol not found in platform.yml: {}').format(method['id'])
            })
    return methods


def validate_platform_package(pkg_dir):
    data = load_platform_package_data(pkg_dir)
    if not data:
        return None
    methods = validate_platform_automation_methods(pkg_dir, platform_data=data)
    existing_methods = get_existing_platform_automation_methods(
        exclude_platform_name=data.get('name')
    )
    existing_ids = {item['id'] for item in existing_methods}
    duplicate_ids = [item['id'] for item in methods if item['id'] in existing_ids]
    if duplicate_ids:
        raise ValidationError({
            'error': _('Platform automation method id already exists: {}').format(
                ', '.join(sorted(set(duplicate_ids)))
            )
        })
    return data


def prepare_platform_data_for_save(pkg_dir, platform_data):
    if platform_data['category'] not in [Category.CUSTOM, Category.WEB]:
        raise ValidationError({'error': _('Only support custom and web platform package')})

    try:
        tp = platform_data['type']
    except KeyError:
        raise ValidationError({'error': _('Missing type in platform.yml')})

    automation_methods = validate_platform_automation_methods(pkg_dir, platform_data=platform_data)
    constraints = AllTypes.get_constraints(platform_data['category'], tp)
    automation_defaults = constraints.get('automation', {})
    if automation_methods:
        automation_defaults = {
            **automation_defaults,
            'ansible_enabled': True,
            **build_platform_automation_defaults(automation_methods)
        }

    platform_data = {
        **platform_data,
        'automation': {
            **automation_defaults,
            **(platform_data.get('automation') or {})
        }
    }
    return platform_data, tp


def save_platform_from_package(pkg_dir, instance=None, created_by=''):
    from assets.serializers.platform import PlatformSerializer
    from assets.models import PlatformAutomation

    data = load_platform_package_data(pkg_dir)
    if not data:
        return None

    data, tp = prepare_platform_data_for_save(pkg_dir, data)
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


def persist_platform_package(pkg_dir, platform_name):
    target_dir = get_persisted_platform_package_dir(platform_name)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    shutil.copytree(pkg_dir, target_dir)
    return target_dir
