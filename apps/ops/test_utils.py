# -*- coding: utf-8 -*-
#

import sys
import os
from django.test import TestCase

from ops.models import Task, AdHoc
from ops.utils import run_adhoc_object


class TestRunAdHoc(TestCase):
    def setUp(self):
        adhoc = Task(name="Test run adhoc")
        adhoc.save()

        self.data = AdHoc(subject=adhoc, run_as_admin=True, pattern='all')
        self.data.tasks = [
            {'name': 'run ls', 'action': {'module': 'shell', 'args': 'ls'}},
            {'name': 'echo ', 'action': {'module': 'shell', 'args': 'echo 123'}},
        ]
        self.data.hosts = [
            "testserver"
        ]

    def test_run(self):
        pass






