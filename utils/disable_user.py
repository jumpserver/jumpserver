import os
import sys

import django

if os.path.exists('../apps'):
    sys.path.insert(0, '../apps')
elif os.path.exists('./apps'):
    sys.path.insert(0, './apps')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
os.environ.setdefault("DJANGO_DEBUG_SHELL", "1")
django.setup()

from users.models import User


def disable_user(username):
    user = User.objects.filter(username=username).first()
    if not user:
        print("Not found user: ", username)
        return

    print("Disable user: ", username)
    user.is_active = False
    user.save(update_fields=['is_active'])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python disable_user.py <username>")
        sys.exit(1)
    username = sys.argv[1]
    disable_user(username)
