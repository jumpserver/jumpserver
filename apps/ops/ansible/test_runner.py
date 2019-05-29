# -*- coding: utf-8 -*-
#

import unittest
import sys

sys.path.insert(0, "../..")

from ops.ansible.runner import AdHocRunner, CommandRunner
from ops.ansible.inventory import BaseInventory


class TestAdHocRunner(unittest.TestCase):
    def setUp(self):
        host_data = [
            {
                "hostname": "testserver",
                "ip": "192.168.244.185",
                "port": 22,
                "username": "root",
                "password": "redhat",
            },
        ]
        inventory = BaseInventory(host_data)
        self.runner = AdHocRunner(inventory)

    def test_run(self):
        tasks = [
            {"action": {"module": "shell", "args": "ls"}, "name": "run_cmd"},
            {"action": {"module": "shell", "args": "whoami"}, "name": "run_whoami"},
        ]
        ret = self.runner.run(tasks, "all")
        print(ret.results_summary)
        print(ret.results_raw)


class TestCommandRunner(unittest.TestCase):
    def setUp(self):
        host_data = [
            {
                "hostname": "testserver",
                "ip": "192.168.244.168",
                "port": 22,
                "username": "root",
                "password": "redhat",
            },
        ]
        inventory = BaseInventory(host_data)
        self.runner = CommandRunner(inventory)

    def test_execute(self):
        res = self.runner.execute('ls', 'all')
        print(res.results_command)
        print(res.results_raw)


if __name__ == "__main__":
    unittest.main()
