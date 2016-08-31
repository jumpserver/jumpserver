# ~*~ coding: utf-8 ~*~


from django.utils import timezone
from django.shortcuts import reverse
from django.test import TestCase, TransactionTestCase
from django.db import IntegrityError
from users.models import User, UserGroup, init_all_models
from django.contrib.auth.models import Permission

from .base import gen_name, gen_username, gen_email, get_role


class UserModelTest(TransactionTestCase):
    def setUp(self):
        init_all_models()

        # 创建一个用户用于测试
        role = get_role()
        user = User(name='test', username='test', email='test@email.org', role=role)
        user.save()

    def test_initial(self):
        self.assertEqual(User.objects.all().count(), 2)

    @property
    def role(self):
        return get_role()

    # 创建一个姓名一致的用户, 应该创建成功
    def test_user_name_duplicate(self):
        user1 = User(name='test', username=gen_username(), password_raw=gen_username(),
                     email=gen_email())
        try:
            user1.save()
            user1.delete()
        except IntegrityError:
            self.assertTrue(0, 'Duplicate <name> not allowed.')

    # 创建一个用户名一致的用户, 应该创建不成功
    def test_user_username_duplicate(self):
        user2 = User(username='test', email=gen_email(), role=self.role)

        with self.assertRaises(IntegrityError):
            user2.save()

    # 创建一个Email一致的用户,应该创建不成功
    def test_user_email_duplicate(self):
        user3 = User(username=gen_username(), email='test@email.org', role=self.role)

        with self.assertRaises(IntegrityError):
            user3.save()

    # 用户过期测试
    def test_user_was_expired(self):
        date = timezone.now() - timezone.timedelta(days=1)
        user = User(name=gen_name(), username=gen_username(),
                    email=gen_email(), role=self.role, date_expired=date)

        self.assertTrue(user.is_expired)

    # 测试用户默认会输入All用户组
    def test_user_with_default_group(self):
        role = get_role()
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

    def test_user_reset_password(self):
        user = User.objects.first()
        token = User.generate_reset_token(user.email)
        new_password = gen_username()
        User.reset_password(token, new_password)
        user_ = User.objects.get(id=user.id)
        self.assertTrue(user_.check_password(new_password))

    def tearDown(self):
        User.objects.all().delete()
        UserGroup.objects.all().delete()


class UserGroupModelTestCase(TransactionTestCase):
    pass



