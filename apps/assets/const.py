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

ADMIN_USER_CONN_CACHE_KEY = "ADMIN_USER_CONN_{}"
TEST_ADMIN_USER_CONN_TASKS = [
    {
        "name": "ping",
        "action": {
            "module": "ping",
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


ASSET_USER_CONN_CACHE_KEY = 'ASSET_USER_CONN_{}_{}'
TEST_ASSET_USER_CONN_TASKS = [
    {
        "name": "ping",
        "action": {
            "module": "ping",
        }
    }
]


TASK_OPTIONS = {
    'timeout': 10,
    'forks': 10,
}

CACHE_KEY_ASSET_BULK_UPDATE_ID_PREFIX = '_KEY_ASSET_BULK_UPDATE_ID_{}'


