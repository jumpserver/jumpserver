# ~*~ coding: utf-8 ~*~

from random import choice
import forgery_py

from django.utils import timezone
from django.shortcuts import reverse
from django.test import TestCase, Client, TransactionTestCase
from django.test.utils import setup_test_environment
from django.db import IntegrityError, transaction
from .models import User, UserGroup, Role, init_all_models
from django.contrib.auth.models import Permission


def gen_username():
    return forgery_py.internet.user_name(True)


def gen_email():
    return forgery_py.internet.email_address()


def gen_name():
    return forgery_py.name.full_name()


class UserModelTest(TransactionTestCase):
    def setUp(self):
        init_all_models()

        # 创建一个用户用于测试
        role = choice(Role.objects.all())
        user = User(name='test', username='test', email='test@email.org', role=role)
        user.save()

    def test_initial(self):
        self.assertEqual(User.objects.all().count(), 2)
        self.assertEqual(Role.objects.all().count(), 3)
        self.assertEqual(UserGroup.objects.all().count(), 1)

    @property
    def role(self):
        return choice(Role.objects.all())

    # 创建一个姓名一致的用户, 应该创建成功
    def test_user_name_duplicate(self):
        user1 = User(name='test', username=gen_username(), password_raw=gen_username(),
                     email=gen_email(), role=self.role)
        try:
            user1.save()
            user1.delete()
        except IntegrityError:
            self.assertTrue(0, 'Duplicate <name> not allowed.')

    # 创建一个用户名一致的用户, 应该创建不成功
    def test_user_username_duplicate(self):
        user2 = User(username='test', email=gen_email(), role=self.role)
        try:
            user2.save()
            self.assertTrue(0, 'Duplicate <username> allowed.')
        except IntegrityError:
            pass

    # 创建一个Email一致的用户,应该创建不成功
    def test_user_email_duplicate(self):
        user3 = User(username=gen_username(), email='test@email.org', role=self.role)
        try:
            user3.save()
            self.assertTrue(0, 'Duplicate <email> allowed.')
        except IntegrityError:
            pass

    # 用户过期测试
    def test_user_was_expired(self):
        date = timezone.now() - timezone.timedelta(days=1)
        user = User(name=gen_name(), username=gen_username(),
                    email=gen_email(), role=self.role, date_expired=date)

        self.assertTrue(user.is_expired())

    # 测试用户默认会输入All用户组
    def test_user_with_default_group(self):
        role = choice(Role.objects.all())
        user = User(username=gen_username(), email=gen_email(), role=role)
        user.save()

        self.assertEqual(user.groups.count(), 1)
        self.assertEqual(user.groups.first().name, 'Default')

    def test_user_password_authenticated(self):
        password = gen_username() * 3
        user = User(username=gen_username(), password_raw=password, role=self.role)
        user.save()
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.check_password(password*2))

    def tearDown(self):
        User.objects.all().delete()
        UserGroup.objects.all().delete()
        Role.objects.all().delete()


class RoleModelTestCase(TransactionTestCase):
    def setUp(self):
        Role.objects.all().delete()
        Role.initial()

    def test_role_initial(self):
        self.assertEqual(Role.objects.all().count(), 3)

    def test_create_new_role(self):
        role = Role(name=gen_name(), comment=gen_name()*3)
        role.save()
        role.permissions = Permission.objects.all()
        role.save()

        self.assertEqual(Role.objects.count(), 4)
        role = Role.objects.last()
        self.assertEqual(role.permissions.all().count(), Permission.objects.all().count())


class UserGroupModelTestCase(TransactionTestCase):
    pass


class UserListViewTests(TestCase):
    def setUp(self):
        init_all_models()
        User.generate_fake()

    def test_list_view_with_one_user(self):
        response = self.client.get(reverse('users:user-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin')
        self.assertQuerysetEqual(response.context['user_list'], [repr(user) for user in User.objects.all()])

    def test_pagination(self):
        response = self.client.get(reverse('users:user-list'))
        self.assertContains(response.status_code, 200)

