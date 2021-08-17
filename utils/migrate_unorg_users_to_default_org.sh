#!/bin/bash
#

python ../apps/manage.py shell << EOF
from users.models import User
from orgs.models import Organization
unorgs_users = [user for user in User.objects.all() if user.orgs.count() == 0]
Organization.default().members.add(*unorgs_users)
EOF
