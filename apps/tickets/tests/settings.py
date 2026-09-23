"""Isolated workflow tests; optionally exercise row locks using PostgreSQL."""
import os
from copy import deepcopy

from jumpserver.settings import *  # noqa

DEBUG = False
DEBUG_DEV = False
DATABASES = deepcopy(DATABASES)
if os.environ.get('WORKFLOW_TEST_POSTGRES') == '1':
    if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        raise RuntimeError('WORKFLOW_TEST_POSTGRES requires a configured PostgreSQL database.')
    # AppConfig.ready() can query the database before the runner starts. Keep
    # those startup hooks away from the development database too.
    DATABASES['default']['NAME'] = 'test_jumpserver_workflow_refactor'
    DATABASES['default']['TEST'] = {'NAME': 'test_jumpserver_workflow_refactor'}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
CACHES = deepcopy(CACHES)
for config in CACHES.values():
    config['KEY_PREFIX'] = 'ticket-workflow-tests'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
LOGGING = deepcopy(LOGGING)
for config in LOGGING.get('loggers', {}).values():
    config['level'] = 'ERROR'
TEST_RUNNER = 'tickets.tests.runner.WorkflowTestRunner'
