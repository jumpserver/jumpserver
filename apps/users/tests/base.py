# ~*~ coding: utf-8 ~*~


from random import choice
import forgery_py

from users.models import User, UserGroup, Role, init_all_models


def gen_username():
    return forgery_py.internet.user_name(True)


def gen_email():
    return forgery_py.internet.email_address()


def gen_name():
    return forgery_py.name.full_name()


def get_role():
    role = choice(Role.objects.all())
    return role