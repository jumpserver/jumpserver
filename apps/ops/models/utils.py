# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from ansible import *
from cron import *
from sudo import *


def generate_fake():
    for cls in (AssetGroup, IDC, AdminUser, SystemUser, Asset):
        cls.generate_fake()