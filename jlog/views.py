# coding:utf-8
from django.db.models import Q
from django.template import RequestContext
from django.shortcuts import render_to_response

from jumpserver.api import *
from jasset.views import httperror
from django.http import HttpResponseNotFound

CONF = ConfigParser()
CONF.read('%s/jumpserver.conf' % BASE_DIR)


def get_user_info(request, offset):
    """ 获取用户信息及环境 """
    env_dic = {'online': 0, 'offline': 1}
    env = env_dic[offset]
    keyword = request.GET.get('keyword', '')
    user_info = get_session_user_info(request)
    user_id, username = user_info[0:2]
    dept_id, dept_name = user_info[3:5]
    ret = [request, keyword, env, username, dept_name]

    return ret


def get_user_log(ret_list):
    """ 获取不同类型用户日志记录 """
    request, keyword, env, username, dept_name = ret_list
    post_all = Log.objects.filter(is_finished=env).order_by('-start_time')
    post_keyword_all = Log.objects.filter(Q(user__contains=keyword) |
                                          Q(host__contains=keyword)) \
        .filter(is_finished=env).order_by('-start_time')

    if is_super_user(request):
        if keyword:
            posts = post_keyword_all
        else:
            posts = post_all

    elif is_group_admin(request):
        if keyword:
            posts = post_keyword_all.filter(dept_name=dept_name)
        else:
            posts = post_all.filter(dept_name=dept_name)

    elif is_common_user(request):
        if keyword:
            posts = post_keyword_all.filter(user=username)
        else:
            posts = post_all.filter(user=username)

    return posts


@require_login
def log_list(request, offset):
    """ 显示日志 """
    header_title, path1, path2 = u'查看日志', u'查看日志', u'在线用户'
    keyword = request.GET.get('keyword', '')
    web_socket_host = CONF.get('websocket', 'web_socket_host')
    posts = get_user_log(get_user_info(request, offset))
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return render_to_response('jlog/log_%s.html' % offset, locals(), context_instance=RequestContext(request))


@require_admin
def log_kill(request):
    """ 杀掉connect进程 """
    pid = request.GET.get('id', '')
    log = Log.objects.filter(pid=pid)
    if log:
        log = log.first()
        dept_name = log.dept_name
        deptname = get_session_user_info(request)[4]
        if is_group_admin(request) and dept_name != deptname:
            return httperror(request, u'Kill失败, 您无权操作!')
        os.kill(int(pid), 9)
        Log.objects.filter(pid=pid).update(is_finished=1, end_time=datetime.datetime.now())
        return render_to_response('jlog/log_offline.html', locals(), context_instance=RequestContext(request))
    else:
        return HttpResponseNotFound(u'没有此进程!')


@require_login
def log_history(request):
    """ 命令历史记录 """
    log_id = request.GET.get('id', 0)
    log = Log.objects.filter(id=int(log_id))
    if log:
        log = log.first()
        dept_name = log.dept_name
        deptname = get_session_user_info(request)[4]
        if is_group_admin(request) and dept_name != deptname:
            return httperror(request, '查看失败, 您无权查看!')

        elif is_common_user(request):
            return httperror(request, '查看失败, 您无权查看!')

        log_his = "%s.his" % log.log_path
        if os.path.isfile(log_his):
            f = open(log_his)
            content = f.read()
            return HttpResponse(content)
        else:
            return httperror(request, '无日志记录, 请查看日志处理脚本是否开启!')


@require_login
def log_search(request):
    """ 日志搜索 """
    offset = request.GET.get('env', '')
    keyword = request.GET.get('keyword', '')
    posts = get_user_log(get_user_info(request, offset))
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return render_to_response('jlog/log_search.html', locals(), context_instance=RequestContext(request))
