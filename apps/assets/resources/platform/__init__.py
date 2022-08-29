import os
import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

platform_ops_methods = []


def get_platform_methods():
    methods = []
    for root, dirs, files in os.walk(BASE_DIR, topdown=False):
        for name in dirs:
            path = os.path.join(root, name)
            rel_path = path.replace(BASE_DIR, '.')
            if len(rel_path.split('/')) != 4:
                continue
            manifest_path = os.path.join(path, 'manifest.yml')
            if not os.path.exists(manifest_path):
                print("Path not exists: {}".format(manifest_path))
                continue
            f = open(manifest_path, 'r')
            try:
                manifest = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(e)
                continue
            current, category, tp, name = rel_path.split('/')
            manifest.update({
                'id': name,
                'category': category,
                'type': tp,
            })
            methods.append(manifest)
    return methods


def get_platform_method(platform, method):
    methods = get_platform_methods()

    def key(m):
        return m.get('method') == method \
               and m['category'] == platform.category \
               and m['type'] == platform.type
    return list(filter(key, methods))
