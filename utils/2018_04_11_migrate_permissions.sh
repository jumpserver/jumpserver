#!/bin/bash
#

python ../apps/manage.py shell << EOF
from perms.models import *

for old in NodePermission.objects.all():
    perm = asset_perm_model.objects.using(db_alias).create(
            name="{}-{}-{}".format(
                old.node.value,
                old.user_group.name,
                old.system_user.name
            ),
            is_active=old.is_active,
            date_expired=old.date_expired,
            created_by=old.date_expired,
            date_created=old.date_created,
            comment=old.comment,
    )
    perm.user_groups.add(old.user_group)
    perm.nodes.add(old.node)
    perm.system_users.add(old.system_user)
EOF

