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


def update_user_password(username, password):
    user = User.objects.filter(username=username).first()
    if not user:
        print("Not found user: ", username)
        return

    print("Update user password: ", username)
    user.set_password(password)
    user.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Reset a local user password.')
    parser.add_argument('username')
    parser.add_argument('--stdin', action='store_true', help='Read the new password from one stdin line')
    args = parser.parse_args()
    if args.stdin:
        password = sys.stdin.readline().rstrip('\r\n')
    else:
        if not sys.stdin.isatty():
            parser.error('Use --stdin for non-interactive password input')
        password = getpass.getpass('New password: ')
        if password != getpass.getpass('Confirm new password: '):
            parser.error('New passwords do not match')
    if not password:
        parser.error('Password must not be empty')
    update_user_password(args.username, password)
