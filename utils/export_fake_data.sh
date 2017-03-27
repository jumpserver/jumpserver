#!/bin/bash
#

python2.7 ../apps/manage.py shell << EOF
from users.models.utils import *
generate_fake()
from assets.models.utils import *
generate_fake()
EOF

python2.7 ../apps/manage.py dbshell << EOF
delete from django_content_type;
delete from auth_permission;
EOF


python2.7 ../apps/manage.py dumpdata > ../apps/fixtures/fake.json
