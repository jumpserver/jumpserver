#!/bin/bash
#

function disable_auth_ldap() {
python3 ../apps/manage.py shell << EOF
from oauth2_provider.models import *
apps = Application.objects.all()
apps.delete()
print("OAuth2 Provider Applications deleted successfully!")
EOF
}

disable_auth_ldap
