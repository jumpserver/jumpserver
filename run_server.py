#!/usr/bin/env python

import os
import subprocess
import time
from threading import Thread

from apps import __version__

try:
    from config import config as CONFIG
except ImportError:
    CONFIG = type('_', (), {'__getattr__': None})()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_DIR = os.path.join(BASE_DIR, 'apps')
HTTP_HOST = CONFIG.HTTP_BIND_HOST or '127.0.0.1'
HTTP_PORT = CONFIG.HTTP_LISTEN_PORT or 8080
LOG_LEVEL = CONFIG.LOG_LEVEL
WORKERS = 4


def start_gunicorn():
    print("- Start Gunicorn WSGI HTTP Server")
    os.chdir(APPS_DIR)
    cmd = "gunicorn jumpserver.wsgi -b {}:{} -w {}".format(HTTP_HOST, HTTP_PORT, WORKERS)
    subprocess.call(cmd, shell=True)


def start_celery():
    print("- Start Celery as Distributed Task Queue")
    os.chdir(APPS_DIR)
    # os.environ.setdefault('PYTHONOPTIMIZE', '1')
    cmd = 'celery -A common worker -l {}'.format(LOG_LEVEL.lower())
    subprocess.call(cmd, shell=True)


def start_beat():
    print("- Start Beat as Periodic Task Scheduler")
    os.chdir(APPS_DIR)
    # os.environ.setdefault('PYTHONOPTIMIZE', '1')
    schduler = "django_celery_beat.schedulers:DatabaseScheduler"
    cmd = 'celery -A common beat  -l {} --scheduler {}'.format(LOG_LEVEL, schduler)
    subprocess.call(cmd, shell=True)


def main():
    print(time.ctime())
    print('Jumpserver version {}, more see https://www.jumpserver.org'.format(
        __version__))
    print('Quit the server with CONTROL-C.')

    threads = []
    for func in (start_gunicorn, start_celery, start_beat):
        t = Thread(target=func, args=())
        threads.append(t)
        t.start()

    for t in threads:
        t.join()


if __name__ == '__main__':
    main()






