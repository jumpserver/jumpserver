#!/usr/bin/python
import argparse
import getpass
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
    user.set_password(new_password)
    user.save()

    return EXIT_SUCCESS


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Change a local user password.')
    parser.add_argument('username')
    parser.add_argument('--stdin', action='store_true', help='Read old and new passwords from two stdin lines')
    args = parser.parse_args()

    try:
        if args.stdin:
            old_password = sys.stdin.readline().rstrip('\r\n')
            new_password = sys.stdin.readline().rstrip('\r\n')
        else:
            if not sys.stdin.isatty():
                parser.error('Use --stdin for non-interactive password input')
            old_password = getpass.getpass('Old password: ')
            new_password = getpass.getpass('New password: ')
            if new_password != getpass.getpass('Confirm new password: '):
                parser.error('New passwords do not match')
        if not old_password or not new_password:
            parser.error('Passwords must not be empty')
        sys.exit(change_user_password(args.username, old_password, new_password))
    except Exception as exc:
        print("Change user password failed:", exc)
        sys.exit(EXIT_UNEXPECTED_ERROR)
