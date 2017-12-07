#!/bin/bash
#

python ../apps/manage.py shell << EOF
from users.models import *
init_model()

from assets.models import *
init_model()

EOF

python ../apps/manage.py dbshell << EOF
delete from auth_permission;
delete from django_content_type;
EOF

python ../apps/manage.py dumpdata > ../apps/fixtures/init.json
