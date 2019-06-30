# -*- coding: utf-8 -*-
#
from django.test import TestCase

from assets.models import Node, SystemUser
from .asset_permission import FlatPermission
from ..models import ActionFlag


class TestFlatPermissionEqual(TestCase):
    def setUp(self):
        node1 = Node(value="parent", key="1:1")
        node2 = Node(value="child", key="1:1:1")

        system_user1 = SystemUser(username="name1", name="name1", priority=20)
        system_user2 = SystemUser(username="name2", name="name2", priority=10)

        action1 = ActionFlag.ALL
        action2 = ActionFlag.CONNECT
        action3 = ActionFlag.UPDOWNLOAD

        perm1 = FlatPermission(node1, system_user1, action1)
        perm2 = FlatPermission(node2, system_user1, action1)
        perm3 = FlatPermission(node2, system_user2, action1)

        self.groups = (
            (perm1, perm2, True),
            (perm1, perm3, True),
        )

    def test_equal(self):
        for k, k2, wanted in self.groups:
            if (k == k2) != wanted:
                print("Not equal {} {}", k, k2)


