import os
import yaml
from functools import partial

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
        if _id in ids[i+1:]:
            raise ValueError("Duplicate id: {}".format(_id))


def get_platform_automation_methods():
    methods = []
    for root, dirs, files in os.walk(BASE_DIR, topdown=False):
        for name in files:
            path = os.path.join(root, name)
            if not path.endswith('manifest.yml'):
                continue

            with open(path, 'r') as f:
                manifest = yaml.safe_load(f)
                check_platform_method(manifest, path)
                manifest['dir'] = os.path.dirname(path)
            methods.append(manifest)

    check_platform_methods(methods)
    return methods


def filter_key(manifest, attr, value):
    manifest_value = manifest.get(attr, '')
    if isinstance(manifest_value, str):
        manifest_value = [manifest_value]
    return value in manifest_value or 'all' in manifest_value


def filter_platform_methods(category, tp, method=None):
    methods = platform_automation_methods
    if category:
        methods = filter(partial(filter_key, attr='category', value=category), methods)
    if tp:
        methods = filter(partial(filter_key, attr='type', value=tp), methods)
    if method:
        methods = filter(lambda x: x['method'] == method, methods)
    return methods


platform_automation_methods = get_platform_automation_methods()


if __name__ == '__main__':
    print(get_platform_automation_methods())
