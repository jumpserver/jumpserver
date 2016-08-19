import forgery_py

from django.test import TestCase, Client
from django.test.utils import setup_test_environment
from .models import User, UserGroup


setup_test_environment()
client = Client()


def create_usergroup(name):
    pass


def get_random_usergroup():
    pass


def create_user(username, name, email, groups):
    pass


class UserListViewTests(TestCase):
    pass
