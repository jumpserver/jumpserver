#!/usr/bin/env python
#
import os
import sys
import subprocess

import redis_lock
from redis import Redis

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIR = os.path.join(BASE_DIR, 'apps')

sys.path.insert(0, BASE_DIR)
from apps.jumpserver.const import CONFIG

os.environ.setdefault('PYTHONOPTIMIZE', '1')
if os.getuid() == 0:
    os.environ.setdefault('C_FORCE_ROOT', '1')

redis = Redis(host=CONFIG.REDIS_HOST, port=CONFIG.REDIS_PORT, password=CONFIG.REDIS_PASSWORD)
scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

cmd = [
    'celery', 'beat',
    '-A', 'ops',
    '-l', 'INFO',
    '--scheduler', scheduler,
    '--max-interval', '60'
]

with redis_lock.Lock(redis, name="beat-distribute-start-lock", expire=60, auto_renewal=True):
    print("Get beat lock start to run it")
    code = subprocess.call(cmd, cwd=APPS_DIR)
    sys.exit(code)
