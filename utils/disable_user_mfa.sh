#!/bin/bash
#

username=$1

if [ -z "${username}" ];then
    echo "No username specify, exit"
    exit 1
fi

function disable_user_mfa() {
python ../apps/manage.py shell << EOF
import sys
from users.models import User
user = User.objects.filter(username="${username}")
if not user:
    print("No user found")
    sys.exit(1)
user.update(otp_level=0)
print("Disable user ${username} success")
EOF
}

disable_user_mfa
