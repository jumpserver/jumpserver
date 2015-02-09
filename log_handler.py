#!/usr/bin/python
#coding: utf-8

import os
import time
import psutil
from datetime import datetime

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'

import django
django.setup()
from jlog.models import Log


def log_hanler(id):
    log = Log.objects.get(id=id)
    if log:
        filename = log.log_path
        if os.path.isfile(filename):
            ret1 = os.system('cat %s | grep "DateTime" > %s.his' % (filename, filename))
            ret2 = os.system('cat %s | grep "\[.*@.*\][\$\#]" >> %s.his' % (filename, filename))
            ret3 = os.system('cat %s | grep "EndTime" >> %s.his' % (filename, filename))
            if (ret1 + ret2 + ret3) == 0:
                print 'Handler %s ok.' % filename
            log.log_finished = True
            log.save()


def set_finish(id):
    log = Log.objects.filter(id=id)
    if log:
        log.update(is_finished=1, end_time=datetime.now())


def kill_pid(pid):
    try:
        os.kill(pid, 9)
    except OSError:
        pass


def get_pids():
    pids1, pids2 = [], []
    pids1_obj = Log.objects.filter(is_finished=0)
    pids2_obj = Log.objects.filter(is_finished=1, log_finished=0)
    for pid_obj in pids1_obj:
        pids1.append((pid_obj.id, pid_obj.pid, pid_obj.log_path, pid_obj.is_finished, pid_obj.log_finished, pid_obj.start_time))
    for pid_obj in pids2_obj:
        pids2.append(pid_obj.id)

    return pids1, pids2


def run():
    pids1, pids2 = get_pids()
    for pid_id in pids2:
        log_hanler(pid_id)

    for pid_id, pid, log_path, is_finished, log_finished, start_time in pids1:
        print pid_id, start_time, type(start_time)
        try:
            file_time = int(os.stat(log_path).st_ctime)
            now_time = int(time.time())
            if now_time - file_time > 18000:
                if psutil.pid_exists(pid):
                    kill_pid(pid)
                set_finish(pid_id)
                log_hanler(pid_id)
        except OSError:
            pass

if __name__ == '__main__':
    while True:
        run()
        time.sleep(5)
