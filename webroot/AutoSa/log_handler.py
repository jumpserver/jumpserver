#!/usr/bin/python
#coding: utf-8

import os
import sys
import time

cur_dir = os.path.dirname(__file__)
sys.path.append('%s/webroot/AutoSa/' % cur_dir)
os.environ['DJANGO_SETTINGS_MODULE'] = 'AutoSa.settings'

from UserManage.models import Logs, Pid


def log_hanler(logid):
    log = Logs.objects.filter(id=logid)
    if log:
        log = log[0]
        filename = log.logfile
        ret1 = os.system('cat %s | grep "DateTime" > %s.his' % (filename, filename))
        ret2 = os.system('cat %s | grep "\[.*@.*\][\$\#]" >> %s.his' % (filename, filename))
        ret3 = os.system('cat %s | grep "EndTime" >> %s.his' % (filename, filename))
        if (ret1 + ret2 + ret3) == 0:
            print 'Handler % ok.' % filename



def set_finish(id):
    logs = Logs.objects.filter(id=id, finish=0)
    if logs:
        structtime_start = time.localtime()
        timestamp_end = int(time.mktime(structtime_start))
        log = logs[0]
        log.finish = 1
        log.end_time = timestamp_end
        log.save()


def kill_pid(pid):
    try:
        os.kill(pid, 9)
    except OSError:
        pass


def pid_exist(pid):
    pid_dir = "/proc/%s" % pid
    if os.path.isdir(pid_dir):
        return True
    else:
        return False


def del_pid(pid_id):
    pid = Pid.objects.filter(id=pid_id)
    if pid:
        pid[0].delete()


def get_pids():
    pids = []
    pids_obj = Pid.objects.all()
    for pid_obj in pids_obj:
        pids.append((pid_obj.id, pid_obj.ppid, pid_obj.cpid, pid_obj.logid, pid_obj.start_time))
    return pids


def run():
    for pid_id, ppid, cpid, logid, start_time in get_pids():
        if pid_exist(cpid):
            if pid_exist(ppid):
                structtime_start = time.localtime()
                timestamp_end = int(time.mktime(structtime_start))
                if timestamp_end - start_time > 7200:
                    kill_pid(ppid)
                    kill_pid(cpid)
                    del_pid(pid_id)
                    set_finish(logid)
                    log_hanler(logid)
            else:
                kill_pid(cpid)
                del_pid(pid_id)
                set_finish(logid)
                log_hanler(logid)
        else:
            del_pid(pid_id)
            set_finish(logid)
            log_hanler(logid)


if __name__ == '__main__':
    while True:
        run()
        time.sleep(0.5)
