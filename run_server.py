#!/usr/bin/env python

import os
import subprocess
import threading
import time
import argparse
import platform
import sys

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
    p = subprocess.Popen(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)
    return p


def start_celery():
    print("- Start Celery as Distributed Task Queue")
    os.chdir(APPS_DIR)
    # Todo: Must set this environment, otherwise not no ansible result return
    os.environ.setdefault('PYTHONOPTIMIZE', '1')

    if platform.platform().startswith("Linux"):
        cmd = """
        id jumpserver || useradd -s /sbin/nologin jumpserver;
        su jumpserver -c 'celery -A common worker -l {}';
        """.format(LOG_LEVEL.lower())
    else:
        cmd = """
        export C_FORCE_ROOT=1;celery -A common worker -l {}
        """.format(LOG_LEVEL.lower())

    p = subprocess.Popen(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)
    return p


def start_beat():
    print("- Start Beat as Periodic Task Scheduler")
    os.chdir(APPS_DIR)
    os.environ.setdefault('PYTHONOPTIMIZE', '1')
    os.environ.setdefault('C_FORCE_ROOT', '1')
    scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
    cmd = 'celery -A common beat  -l {} --scheduler {} --max-interval 60 '.format(LOG_LEVEL, scheduler)
    p = subprocess.Popen(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)
    return p


def start_service(services):
    print(time.ctime())
    print('Jumpserver version {}, more see https://www.jumpserver.org'.format(
        __version__))
    print('Quit the server with CONTROL-C.')

    processes = {}
    services_all = {
         "gunicorn": start_gunicorn,
         "celery": start_celery,
         "beat": start_beat
    }

    if 'all' in services:
        for name, func in services_all.items():
            processes[name] = func()
    else:
        for name in services:
            func = services_all.get(name)
            processes[name] = func()

    stop_event = threading.Event()
    while not stop_event.is_set():
        for name, proc in processes.items():
            if proc.poll() is not None:
                print("\n\n" + "####"*10 + "  ERROR OCCUR  " + "####"*10)
                print("Start service {} [FAILED]".format(name))
                for _, p in processes.items():
                    p.terminate()
                stop_event.set()
                print("Exited".format(name))
                break
        time.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Jumpserver start tools")
    parser.add_argument("services", type=str, nargs='+', default="all",
                        choices=("all", "gunicorn", "celery", "beat"),
                        help="The service to start",
                        )
    args = parser.parse_args()
    start_service(args.services)


