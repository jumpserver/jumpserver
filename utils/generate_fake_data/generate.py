#!/usr/bin/env python
#
import os
import sys
import django
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APPS_DIR = os.path.join(BASE_DIR, 'apps')
sys.path.insert(0, APPS_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from resources.assets import AssetsGenerator, NodesGenerator, SystemUsersGenerator, AdminUsersGenerator
from resources.users import UserGroupGenerator, UserGenerator
from resources.perms import AssetPermissionGenerator
# from resources.system import StatGenerator


resource_generator_mapper = {
    'asset': AssetsGenerator,
    'node': NodesGenerator,
    'system_user': SystemUsersGenerator,
    'admin_user': AdminUsersGenerator,
    'user': UserGenerator,
    'user_group': UserGroupGenerator,
    'asset_permission': AssetPermissionGenerator,
    # 'stat': StatGenerator
}


def main():
    parser = argparse.ArgumentParser(description='Generate fake data')
    parser.add_argument(
        'resource', type=str,
        choices=resource_generator_mapper.keys(),
        help="resource to generate"
    )
    parser.add_argument('-c', '--count', type=int, default=100)
    parser.add_argument('-b', '--batch_size', type=int, default=100)
    parser.add_argument('-o', '--org', type=str, default='')
    args = parser.parse_args()
    resource, count, batch_size, org_id = args.resource, args.count, args.batch_size, args.org
    generator_cls = resource_generator_mapper[resource]
    generator = generator_cls(org_id=org_id, batch_size=batch_size)
    generator.generate(count)


if __name__ == '__main__':
    main()
