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


def update_user_password(username, password):
    user = User.objects.filter(username=username).first()
    if not user:
        print("Not found user: ", username)
        return

    print("Update user password: ", username)
    user.set_password(password)
    user.save()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python update_user_password.py <username> <password>")
        sys.exit(1)
    username = sys.argv[1]
    password = sys.argv[2]
    update_user_password(username, password)