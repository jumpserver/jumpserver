# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

UPDATE_ASSETS_HARDWARE_TASKS = [
   {
       'name': "setup",
       'action': {
           'module': 'setup'
       }
   }
]

TEST_ADMIN_USER_CONN_TASKS = [
    {
        "name": "ping",
        "action": {
            "module": "ping",
        }
    }
]
TEST_WINDOWS_ADMIN_USER_CONN_TASKS = [
    {
        "name": "ping",
        "action": {
            "module": "win_ping",
        }
    }
]

ASSET_ADMIN_CONN_CACHE_KEY = "ASSET_ADMIN_USER_CONN_{}"

SYSTEM_USER_CONN_CACHE_KEY = "SYSTEM_USER_CONN_{}"
TEST_SYSTEM_USER_CONN_TASKS = [
   {
       "name": "ping",
       "action": {
           "module": "ping",
       }
   }
]
TEST_WINDOWS_SYSTEM_USER_CONN_TASKS = [
    {
        "name": "ping",
        "action": {
            "module": "win_ping",
        }
    }
]

TEST_ASSET_USER_CONN_TASKS = [
    {
        "name": "ping",
        "action": {
            "module": "ping",
        }
    }
]
TEST_WINDOWS_ASSET_USER_CONN_TASKS = [
    {
        "name": "ping",
        "action": {
            "module": "win_ping",
        }
    }
]


TASK_OPTIONS = {
    'timeout': 10,
    'forks': 10,
}

CACHE_KEY_ASSET_BULK_UPDATE_ID_PREFIX = '_KEY_ASSET_BULK_UPDATE_ID_{}'
CONN_UNREACHABLE, CONN_REACHABLE, CONN_UNKNOWN = range(0, 3)
CONNECTIVITY_CHOICES = (
    (CONN_UNREACHABLE, _("Unreachable")),
    (CONN_REACHABLE, _('Reachable')),
    (CONN_UNKNOWN, _("Unknown")),
)

