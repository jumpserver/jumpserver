# -*- coding: utf-8 -*-
#

import unittest
import sys

sys.path.insert(0, "../..")

from ops.ansible.runner import AdHocRunner, CommandRunner


class TestAdHocRunner(unittest.TestCase):
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
        self.runner = AdHocRunner(hosts=host_data)

    def test_run(self):
        tasks = [
            {"action": {"module": "shell", "args": "ls"}},
            {"action": {"module": "shell", "args": "whoami"}},
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
        self.runner = CommandRunner(hosts=host_data)

    def test_execute(self):
        res = self.runner.execute('ls', 'all')
        print(res.results_command)


if __name__ == "__main__":
    unittest.main()
