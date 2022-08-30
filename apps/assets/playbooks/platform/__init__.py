import os
import yaml
from functools import partial

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def check_platform_method(manifest):
    required_keys = ['category', 'method', 'name', 'id']
    less_key = set(required_keys) - set(manifest.keys())
    if less_key:
        raise ValueError("Manifest missing keys: {}".format(less_key))
    return True


def get_platform_methods():
    methods = []
    for root, dirs, files in os.walk(BASE_DIR, topdown=False):
        for name in dirs:
            path = os.path.join(root, name)
            rel_path = path.replace(BASE_DIR, '.')
            if len(rel_path.split('/')) != 3:
                continue
            manifest_path = os.path.join(path, 'manifest.yml')
            if not os.path.exists(manifest_path):
                continue

            with open(manifest_path, 'r') as f:
                manifest = yaml.safe_load(f)
                check_platform_method(manifest)

            methods.append(manifest)
    return methods


def filter_key(manifest, attr, value):
    manifest_value = manifest.get(attr, '')
    if manifest_value == 'all':
        return True
    if isinstance(manifest_value, str):
        manifest_value = [manifest_value]
    return value in manifest_value


def filter_platform_methods(category, tp, method):
    methods = platform_ops_methods
    if category:
        methods = filter(partial(filter_key, attr='category', value=category), methods)
    if tp:
        methods = filter(partial(filter_key, attr='type', value=tp), methods)
    if method:
        methods = filter(lambda x: x['method'] == method, methods)
    return methods


platform_ops_methods = get_platform_methods()


if __name__ == '__main__':
    print(get_platform_methods())
