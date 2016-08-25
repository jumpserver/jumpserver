from __future__ import absolute_import
from celery import Celery

# import traceback

# # Import project config setting
# try:
#     from config import config as env_config, env
#     JMS_CONF = env_config.get(env, 'default')()
#     print "ok"
# except ImportError:
#     traceback.print_exc()
#     JMS_CONF = type('_', (), {'__getattr__': None})()
#     print "false"

app = Celery('common',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0',
             include=['ops.tasks'])


