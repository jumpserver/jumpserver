#!/bin/bash
#

python ../apps/manage.py dbshell << EOF
delete from django_content_type;
delete from auth_permission;
EOF


python ../apps/manage.py dumpdata > ../apps/fixtures/init.json
