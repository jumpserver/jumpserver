#!/bin/bash
#

python2.7 ../apps/manage.py shell << EOF
from users.models import *
init_all_models()

from assets.models import *
init_all_models()
EOF


python2.7 ../apps/manage.py dbshell << EOF
delete from django_content_type;
delete from auth_permission;
EOF

python2.7 ../apps/manage.py dumpdata > ../apps/fixtures/init.json
