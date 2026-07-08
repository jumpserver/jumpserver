#!/usr/bin/python
import os
import sys

import django

if os.path.exists('../apps'):
    sys.path.insert(0, '../apps')
elif os.path.exists('./apps'):
    sys.path.insert(0, './apps')

os.environ.setdefault("DJANGO_DEBUG_SHELL", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from users.models import User


EXIT_SUCCESS = 0
EXIT_USAGE_ERROR = 1
EXIT_USER_NOT_FOUND = 10
EXIT_USER_NOT_LOCAL = 11
EXIT_OLD_PASSWORD_MISMATCH = 12
EXIT_UNEXPECTED_ERROR = 20


def change_user_password(username, old_password, new_password):
    user = User.objects.filter(username=username).first()
    if not user:
        print("Not found user:", username)
        return EXIT_USER_NOT_FOUND

    if not user.is_local:
        print("User is not local:", username)
        return EXIT_USER_NOT_LOCAL

    if user.check_password(new_password):
        print("User password already updated:", username)
        return EXIT_SUCCESS

    if not user.check_password(old_password):
        print("Old password mismatch:", username)
        return EXIT_OLD_PASSWORD_MISMATCH

    print("Change user password:", username)
    user.reset_password(new_password=new_password)
    return EXIT_SUCCESS


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python change_user_password.py <username> <old_password> <new_password>")
        sys.exit(EXIT_USAGE_ERROR)

    try:
        username = sys.argv[1]
        old_password = sys.argv[2]
        new_password = sys.argv[3]
        sys.exit(change_user_password(username, old_password, new_password))
    except Exception as exc:
        print("Change user password failed:", exc)
        sys.exit(EXIT_UNEXPECTED_ERROR)
