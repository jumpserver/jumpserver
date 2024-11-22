import json
import os
from functools import partial

from common.utils.yml import yaml_load_with_i18n


def check_platform_method(manifest, manifest_path):
    required_keys = ['category', 'method', 'name', 'id', 'type']
    less_key = set(required_keys) - set(manifest.keys())
    if less_key:
        raise ValueError("Manifest missing keys: {}, {}".format(less_key, manifest_path))
    if not isinstance(manifest['type'], list):
        raise ValueError("Manifest type must be a list: {}".format(manifest_path))
    return True


def check_platform_methods(methods):
    ids = [m['id'] for m in methods]
    for i, _id in enumerate(ids):
        if _id in ids[i + 1:]:
            raise ValueError("Duplicate id: {}".format(_id))


def generate_serializer(data):
    from common.serializers import create_serializer_class
    params = data.pop('params', None)
    if not params:
        return None
    serializer_name = data['id'].title().replace('_', '') + 'Serializer'
    return create_serializer_class(serializer_name, params)


def get_platform_automation_methods(path, lang=None):
    methods = []
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            path = os.path.join(root, name)
            if not path.endswith('manifest.yml'):
                continue

            with open(path, 'r', encoding='utf8') as f:
                manifest = yaml_load_with_i18n(f, lang=lang)
                check_platform_method(manifest, path)
                manifest['dir'] = os.path.dirname(path)
                manifest['params_serializer'] = generate_serializer(manifest)
            methods.append(manifest)

    check_platform_methods(methods)
    return methods


def filter_key(manifest, attr, value):
    manifest_value = manifest.get(attr, '')
    if isinstance(manifest_value, str):
        manifest_value = [manifest_value]
    return value in manifest_value or 'all' in manifest_value


def filter_platform_methods(category, tp_name, method=None, methods=None):
    methods = platform_automation_methods if methods is None else methods
    if category:
        methods = filter(partial(filter_key, attr='category', value=category), methods)
    if tp_name:
        methods = filter(partial(filter_key, attr='type', value=tp_name), methods)
    if method:
        methods = filter(lambda x: x['method'] == method, methods)
    return methods


def sorted_methods(methods):
    return sorted(methods, key=lambda x: x.get('priority', 10))


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
platform_automation_methods = get_platform_automation_methods(BASE_DIR)

if __name__ == '__main__':
    print(json.dumps(platform_automation_methods, indent=4))
