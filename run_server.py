#!/usr/bin/env python

import os
import subprocess
import threading
import time
import argparse
import platform

from apps import __version__

try:
    from config import config as CONFIG
except ImportError:
    CONFIG = type('_', (), {'__getattr__': None})()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_DIR = os.path.join(BASE_DIR, 'apps')
HTTP_HOST = CONFIG.HTTP_BIND_HOST or '127.0.0.1'
HTTP_PORT = CONFIG.HTTP_LISTEN_PORT or 8080
DEBUG = CONFIG.DEBUG
LOG_LEVEL = CONFIG.LOG_LEVEL
WORKERS = 4

EXIT_EVENT = threading.Event()
EXIT_MSGS = []


try:
    os.makedirs(os.path.join(BASE_DIR, "data", "static"))
    os.makedirs(os.path.join(BASE_DIR, "data", "media"))
except:
    pass


def make_migrations():
    print("Check database change, make migrations")
    os.chdir(os.path.join(BASE_DIR, 'utils'))
    subprocess.call('bash make_migrations.sh', shell=True)


def collect_static():
    print("Collect static files")
    os.chdir(os.path.join(BASE_DIR, 'apps'))
    subprocess.call('python manage.py collectstatic --no-input', shell=True)


def start_gunicorn():
    print("- Start Gunicorn WSGI HTTP Server")
    make_migrations()
    collect_static()
    os.chdir(APPS_DIR)
    cmd = "gunicorn jumpserver.wsgi -b {}:{} -w {}".format(HTTP_HOST, HTTP_PORT, WORKERS)
    if DEBUG:
        cmd += " --reload"
    subprocess.call(cmd, shell=True)
    EXIT_MSGS.append("Gunicorn start failed")
    EXIT_EVENT.set()


def start_celery():
    print("- Start Celery as Distributed Task Queue")
    os.chdir(APPS_DIR)
    # Todo: Must set this environment, otherwise not no ansible result return
    os.environ.setdefault('PYTHONOPTIMIZE', '1')

    if platform.platform().startswith("Linux"):
        cmd = """
        id jumpserver || useradd -s /sbin/nologin jumpserver;
        su jumpserver -c 'celery -A common worker -l {}'
        """.format(LOG_LEVEL.lower())
    else:
        cmd = """
        export C_FORCE_ROOT=1;celery -A common worker -l {}'
        """.format(LOG_LEVEL.lower())

    subprocess.call(cmd, shell=True)
    EXIT_MSGS.append("Celery start failed")
    EXIT_EVENT.set()


def start_beat():
    print("- Start Beat as Periodic Task Scheduler")
    os.chdir(APPS_DIR)
    os.environ.setdefault('PYTHONOPTIMIZE', '1')
    os.environ.setdefault('C_FORCE_ROOT', '1')
    scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
    cmd = 'celery -A common beat  -l {} --scheduler {} --max-interval 5 '.format(LOG_LEVEL, scheduler)
    subprocess.call(cmd, shell=True)
    EXIT_MSGS.append("Beat start failed")
    EXIT_EVENT.set()


def start_service(services):
    make_migrations()

    print(time.ctime())
    print('Jumpserver version {}, more see https://www.jumpserver.org'.format(
        __version__))
    print('Quit the server with CONTROL-C.')

    threads = []
    if 'gunicorn' in args.services:
        threads.append(threading.Thread(target=start_gunicorn, args=()))
    if 'celery' in args.services:
        threads.append(threading.Thread(target=start_celery, args=()))
    if 'beat' in args.services:
        threads.append(threading.Thread(target=start_beat, args=()))
    if 'all' in args.services:
        _threads = []
        for func in (start_gunicorn, start_celery, start_beat):
            t = threading.Thread(target=func, args=())
            _threads.append(t)
        threads = _threads

    for t in threads:
        t.start()

    if EXIT_EVENT.wait():
        print("\n\n" + "####" * 30)
        print("\n".join(EXIT_MSGS))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Jumpserver start tools")
    parser.add_argument("services", type=str, nargs='+', default="all",
                        choices=("all", "gunicorn", "celery", "beat"),
                        help="The service to start",
                        )
    args = parser.parse_args()
    start_service(args.services)


