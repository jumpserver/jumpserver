# -*- coding: utf-8 -*-
#

import sys
import unittest


sys.path.insert(0, '../..')
from ops.ansible.inventory import BaseInventory


class TestJMSInventory(unittest.TestCase):
    def setUp(self):
        host_list = [{
            "hostname": "testserver1",
            "ip": "102.1.1.1",
            "port": 22,
            "username": "root",
            "password": "password",
            "private_key": "/tmp/private_key",
            "become": {
                "method": "sudo",
                "user": "root",
                "pass": None,
            },
            "groups": ["group1", "group2"],
            "vars": {"sexy": "yes"},
        }, {
            "hostname": "testserver2",
            "ip": "8.8.8.8",
            "port": 2222,
            "username": "root",
            "password": "password",
            "private_key": "/tmp/private_key",
            "become": {
                "method": "su",
                "user": "root",
                "pass": "123",
            },
            "groups": ["group3", "group4"],
            "vars": {"love": "yes"},
        }]

        self.inventory = BaseInventory(host_list=host_list)

    def test_hosts(self):
        print("#"*10 + "Hosts" + "#"*10)
        for host in self.inventory.hosts:
            print(host)

    def test_groups(self):
        print("#" * 10 + "Groups" + "#" * 10)
        for group in self.inventory.groups:
            print(group)

    def test_group_all(self):
        print("#" * 10 + "all group hosts" + "#" * 10)
        group = self.inventory.get_group('all')
        print(group.hosts)


if __name__ == '__main__':
    unittest.main()
