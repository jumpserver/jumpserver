#!/bin/bash
#

python ../apps/manage.py shell << EOF
from users.models.utils import *
generate_fake()
from assets.models.utils import *
generate_fake()
EOF

python ../apps/manage.py dbshell << EOF
delete from auth_permission;
delete from django_content_type;
EOF


python ../apps/manage.py dumpdata > ../apps/fixtures/fake.json
