# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from ansible import *
from cron import *
from sudo import *

__all__ = ["generate_fake"]


def generate_fake():
    for cls in (Tasker, AnsiblePlay, AnsibleTask, AnsibleHostResult, CronTable,
                HostAlia, UserAlia, CmdAlia, RunasAlia, Privilege, Sudo):
        cls.generate_fake()