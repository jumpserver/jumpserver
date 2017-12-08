# -*- coding: utf-8 -*-
#

import sys
import os
from django.test import TestCase

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
from ops.models import AdHoc, AdHocData
from ops.utils import run_adhoc


class TestRunAdHoc(TestCase):
    def setUp(self):
        adhoc = AdHoc(name="Test run adhoc")
        adhoc.save()

        self.data = AdHocData(subject=adhoc, run_as_admin=True, pattern='all')
        self.data.tasks = [
            {'name': 'run ls', 'action': {'module': 'shell', 'args': 'ls'}},
            {'name': 'echo ', 'action': {'module': 'shell', 'args': 'echo 123'}},
        ]
        self.data.hosts = [
            "testserver"
        ]

    def test_run(self):
        pass






