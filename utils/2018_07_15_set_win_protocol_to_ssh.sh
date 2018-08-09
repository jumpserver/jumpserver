#!/bin/bash
#

python ../apps/manage.py shell << EOF
from assets.models import Asset

Asset.objects.filter(platform__startswith='Win').update(protocol='rdp')

EOF
