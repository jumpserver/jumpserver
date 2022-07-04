#!/usr/bin/env python
#
import os
import sys
import signal
import subprocess

import redis_lock
from redis import Redis

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIR = os.path.join(BASE_DIR, 'apps')
CERTS_DIR = os.path.join(BASE_DIR, 'data', 'certs')

sys.path.insert(0, APPS_DIR)
from jumpserver import settings

os.environ.setdefault('PYTHONOPTIMIZE', '1')
if os.getuid() == 0:
    os.environ.setdefault('C_FORCE_ROOT', '1')

params = {
    'host': settings.REDIS_HOST,
    'port': settings.REDIS_PORT,
    'password': settings.REDIS_PASSWORD,
    'ssl': settings.REDIS_USE_SSL,
    'ssl_cert_reqs': settings.REDIS_SSL_REQUIRED,
    'ssl_keyfile': settings.REDIS_SSL_KEY,
    'ssl_certfile': settings.REDIS_SSL_CERT,
    'ssl_ca_certs': settings.REDIS_SSL_CA
}
print("Pamras: ", params)
redis = Redis(**params)
scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
processes = []
cmd = [
    'celery',
    '-A', 'ops',
    'beat',
    '-l', 'INFO',
    '--scheduler', scheduler,
    '--max-interval', '60'
]


def stop_beat_process(sig, frame):
    for p in processes:
        os.kill(p.pid, 15)


def main():
    # 父进程结束通知子进程结束
    signal.signal(signal.SIGTERM, stop_beat_process)

    with redis_lock.Lock(redis, name="beat-distribute-start-lock", expire=60, auto_renewal=True):
        print("Get beat lock start to run it")
        process = subprocess.Popen(cmd, cwd=APPS_DIR)
        processes.append(process)
        process.wait()


if __name__ == '__main__':
    main()
