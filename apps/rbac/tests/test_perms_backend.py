# -*- coding: utf-8 -*-
#
from django.test import TestCase
import uuid

from users.models import User
from django.contrib.auth.models import Permission
from orgs.models import Organization
from rbac.models import Role, SystemRoleBinding, OrgRoleBinding, NamespaceRoleBinding

from rbac.backends import RBACBackend


class SystemScopeTestCase(TestCase):
    user: User
    role: Role
    role_binding: SystemRoleBinding

    app = 'accounts'
    codename = 'add_account'

    def setUp(self) -> None:
        username = str(uuid.uuid4())
        name = username
        email = f'{name}@fit2cloud.com'
        self.user, created = User.objects.get_or_create(username=username, name=username, email=email)
        self.role, created = Role.objects.get_or_create(name='Account creator', type=Role.TypeChoices.system)
        account_create_permissions = Permission.objects.filter(codename=self.codename, content_type__app_label=self.app)
        self.role.permissions.set(account_create_permissions)
        self.role_binding = SystemRoleBinding.objects.create(user=self.user, role=self.role)

    def test_has_system_perm(self):
        backend = RBACBackend()
        has = backend.has_perm(self.user, f'{self.app}.{self.codename}')
        self.assertTrue(has, 'Should be has add account perm, but not')

        not_has = backend.has_perm(self.user, f'{self.app}.del_account')
        self.assertFalse(not_has, 'Should be not has del account perm, but not')

    def tearDown(self) -> None:
        self.user.delete()
        self.role_binding.delete()
        self.role.delete()


class OrgScopeTestCase(TestCase):
    user: User
    role: Role
    org_role_binding: SystemRoleBinding

    app = 'accounts'
    codename = 'add_account'

    def setUp(self) -> None:
        username = str(uuid.uuid4())
        name = username
        email = f'{name}@fit2cloud.com'
        self.user, created = User.objects.get_or_create(username=username, name=username, email=email)
        self.role, created = Role.objects.get_or_create(name='Role account creator', type=Role.TypeChoices.org)
        account_create_permissions = Permission.objects.filter(codename=self.codename, content_type__app_label=self.app)
        self.role.permissions.set(account_create_permissions)
        self.org, created = Organization.objects.get_or_create(name='Test org')
        self.org_role_binding = OrgRoleBinding.objects.create(user=self.user, role=self.role, org=self.org)

    def test_has_system_perm(self):
        backend = RBACBackend()
        has = backend.has_perm(self.user, f'org:{self.org.id}|{self.app}.{self.codename}')
        self.assertTrue(has, 'Should be has add account perm, but not')

        not_has = backend.has_perm(self.user, f'org:{self.org.id}|{self.app}.del_account')
        self.assertFalse(not_has, 'Should be not has del account perm, but not')

    def tearDown(self) -> None:
        self.user.delete()
        self.org_role_binding.delete()
        self.role.delete()

