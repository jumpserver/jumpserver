#!/bin/bash
#

function disable_auth_ldap() {
python3 ../apps/manage.py shell << EOF
import sys
from settings.models import Setting
auth_ldap = Setting.objects.get(name='AUTH_LDAP')
if not auth_ldap:
    print("No AUTH_LDAP config")
    sys.exit(1)
if auth_ldap.value == 'false':
    print("AUTH_LDAP is already disabled")
    sys.exit(1)
auth_ldap.value = 'false'
auth_ldap.save()
auth_ldap.refresh_setting()
print("Disable AUTH_LDAP success!")
EOF
}

disable_auth_ldap
