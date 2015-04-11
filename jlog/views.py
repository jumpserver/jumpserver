# coding:utf-8
import os
import ConfigParser
from datetime import datetime

from django.db.models import Q
from django.http import HttpResponse
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response

from connect import BASE_DIR
from jlog.models import Log
from jumpserver.views import pages
from juser.models import User, DEPT
from jumpserver.api import get_user_dept, is_super_user, is_group_admin, is_common_user, require_admin, require_login

CONF = ConfigParser.ConfigParser()
CONF.read('%s/jumpserver.conf' % BASE_DIR)


def get_user_log(request, keyword, env, username, dept_name):
    if is_super_user(request):
        if keyword:
            posts = Log.objects.filter(Q(user__contains=keyword) | Q(host__contains=keyword)) \
                .filter(is_finished=env).order_by('-start_time')
        else:
            posts = Log.objects.filter(is_finished=env).order_by('-start_time')

    elif is_group_admin(request):
        if keyword:
            posts = Log.objects.filter(Q(user__contains=keyword) | Q(host__contains=keyword)) \
                .filter(is_finished=env).filter(dept_name=dept_name).order_by('-start_time')
        else:
            posts = Log.objects.filter(is_finished=env).filter(dept_name=dept_name).order_by('-start_time')

    elif is_common_user(request):
        if keyword:
            posts = Log.objects.filter(user=username).filter(Q(user__contains=keyword) | Q(host__contains=keyword))\
                .filter(is_finished=env).order_by('-start_time')
        else:
            posts = Log.objects.filter(is_finished=env).filter(user=username).order_by('-start_time')
    return posts


@require_login
def log_list(request, offset):
    header_title, path1, path2 = u'查看日志', u'查看日志', u'在线用户'
    web_socket_host = CONF.get('websocket', 'web_socket_host')
    env_dic = {'online': 0, 'offline': 1}
    env = env_dic[offset]
    keyword = request.GET.get('keyword')
    dept_id = get_user_dept(request)
    dept_name = DEPT.objects.get(id=dept_id).name
    user_id = request.session.get('user_id')
    username = User.objects.get(id=user_id).username
    posts = get_user_log(request, keyword, env, username, dept_name)
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return render_to_response('jlog/log_%s.html' % offset, locals(), context_instance=RequestContext(request))


@require_admin
def log_kill(request, offset):
    pid = offset
    if pid:
        os.kill(int(pid), 9)
        Log.objects.filter(pid=pid).update(is_finished=1, end_time=datetime.now())
        return HttpResponseRedirect('jlog/log_offline.html', locals(), context_instance=RequestContext(request))


@require_login
def log_history(request):
    if request.method == 'GET':
        id = request.GET.get('id', 0)
        log = Log.objects.get(id=int(id))
        if log:
            log_his = "%s.his" % log.log_path
            if os.path.isfile(log_his):
                f = open(log_his)
                content = f.read()
                return HttpResponse(content)


@require_login
def log_search(request):
    keyword = request.GET.get('keyword')
    offset = request.GET.get('env')
    dept_id = get_user_dept(request)
    dept_name = DEPT.objects.get(id=dept_id).name
    user_id = request.session.get('user_id')
    username = User.objects.get(id=user_id).username

    env_dic = {'online': 0, 'offline': 1}
    env = env_dic[offset]
    posts = get_user_log(request, keyword, env, username, dept_name)
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return render_to_response('jlog/log_search.html', locals(), context_instance=RequestContext(request))
