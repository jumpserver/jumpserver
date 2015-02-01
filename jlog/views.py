# coding:utf-8
import os
import ConfigParser
from datetime import datetime
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.paginator import Paginator, EmptyPage

from connect import BASE_DIR
from jlog.models import Log

CONF = ConfigParser.ConfigParser()
CONF.read('%s/jumpserver.conf' % BASE_DIR)


def jlog_list(request, offset='online'):
    header_title, path1, path2 = u'查看日志 | Log List.', u'查看日志', u'日志列表'
    web_socket_host = CONF.get('websocket', 'web_socket_host')
    online = Log.objects.filter(is_finished=0)
    offline = Log.objects.filter(is_finished=1)

    return render_to_response('jlog/log_list.html', locals())


def jlog_kill(request, offset):
    pid = offset
    if pid:
        os.kill(int(pid), 9)
        Log.objects.filter(pid=pid).update(is_finished=1, end_time=datetime.now())
        return HttpResponseRedirect('jlog/log_list.html', locals())