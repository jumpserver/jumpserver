# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from ansible import *

__all__ = ["generate_fake"]


def generate_fake():
    for cls in (TaskRecord, AnsiblePlay, AnsibleTask, AnsibleHostResult):
        cls.generate_fake()