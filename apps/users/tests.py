# ~*~ coding: utf-8 ~*~

from random import choice
import forgery_py

from django.utils import timezone
from django.test import TestCase, Client, TransactionTestCase
from django.test.utils import setup_test_environment
from django.db import IntegrityError, transaction
from .models import User, UserGroup, Role, init_all_models


setup_test_environment()
client = Client()


def create_usergroup(name):
    pass


def get_random_usergroup():
    pass


def create_user(username, name, email, groups):
    pass


def gen_username():
    return forgery_py.internet.user_name(True)


def gen_email():
    return forgery_py.internet.email_address()


def gen_name():
    return forgery_py.name.full_name()


class UserModelTest(TransactionTestCase):
    def setUp(self):
        init_all_models()

    def test_user_duplicate(self):
        # 创建一个基准测试用户
        role = choice(Role.objects.all())
        user = User(name='test', username='test', email='test@email.org', role=role)
        user.save()

        # 创建一个姓名一致的用户, 应该创建成功
        user1 = User(name='test', username=gen_username(), password_raw=gen_username(),
                     email=gen_email(), role=role)
        try:
            user1.save()
            user1.delete()
        except IntegrityError:
            self.assertTrue(0, 'Duplicate <name> not allowed.')

        # 创建一个用户名一致的用户, 应该创建不成功
        user2 = User(username='test', email=gen_email(), role=role)

        try:
            user2.save()
            self.assertTrue(0, 'Duplicate <username> allowed.')
        except IntegrityError:
            pass

        # 创建一个Email一致的用户,应该创建不成功
        user3 = User(username=gen_username(), email='test@email.org', role=role)
        try:
            user3.save()
            self.assertTrue(0, 'Duplicate <email> allowed.')
        except IntegrityError:
            pass

    def test_user_was_expired(self):
        role = choice(Role.objects.all())
        date = timezone.now() - timezone.timedelta(days=1)
        user = User(name=gen_name(), username=gen_username(),
                    email=gen_email(), role=role, date_expired=date)

        self.assertTrue(user.is_expired())

    def test_user_with_default_group(self):
        role = choice(Role.objects.all())
        user = User(username=gen_username(), email=gen_email(), role=role)
        user.save()

        self.assertEqual(user.groups.count(), 1)
        self.assertEqual(user.groups.first().name, 'All')


class UserListViewTests(TestCase):
    pass
