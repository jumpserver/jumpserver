#!/bin/bash
#

python ../apps/manage.py shell << EOF
from django.core.cache import cache

cache.delete_pattern('_LOGIN_BLOCK_*')
cache.delete_pattern('_LOGIN_LIMIT_*')

EOF
