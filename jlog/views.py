# coding:utf-8
from django.db.models import Q
from django.template import RequestContext
from django.shortcuts import render_to_response

from jumpserver.api import *
from django.http import HttpResponseNotFound
from jlog.log_api import renderTemplate

from models import Log
from jumpserver.settings import web_socket_host


def log_list(request, offset):
    """ 显示日志 """
    header_title, path1, path2 = u'查看日志', u'查看日志', u'在线用户'
    # posts = get_user_log(get_user_info(request, offset))
    date_seven_day = request.GET.get('start', '')
    date_now_str = request.GET.get('end', '')
    username_list = request.GET.getlist('username', [])
    host_list = request.GET.getlist('host', [])
    cmd = request.GET.get('cmd', '')
    print date_seven_day, date_now_str
    if offset == 'online':
        posts = Log.objects.filter(is_finished=False).order_by('-start_time')
    else:
        posts = Log.objects.filter(is_finished=True).order_by('-start_time')
        username_all = set([log.user for log in Log.objects.all()])
        ip_all = set([log.host for log in Log.objects.all()])

        if date_seven_day and date_now_str:
            datetime_start = datetime.datetime.strptime(date_seven_day, '%m/%d/%Y %H:%M:%S')
            datetime_end = datetime.datetime.strptime(date_now_str, '%m/%d/%Y %H:%M:%S')
            posts = posts.filter(start_time__gte=datetime_start).filter(start_time__lte=datetime_end)

        if username_list:
            print username_list
            posts = posts.filter(user__in=username_list)

        if host_list:
            posts = posts.filter(host__in=host_list)
        print posts
        if cmd:
            log_id_list = set([log.log_id for log in TtyLog.objects.filter(cmd__contains=cmd)])
            print [post.id for post in posts]
            posts = posts.filter(id__in=log_id_list)
            print posts
        else:
            date_now = datetime.datetime.now()
            date_now_str = date_now.strftime('%m/%d/%Y')
            date_seven_day = (date_now + datetime.timedelta(days=-7)).strftime('%m/%d/%Y')

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return render_to_response('jlog/log_%s.html' % offset, locals(), context_instance=RequestContext(request))

#
# def log_kill(request):
#     """ 杀掉connect进程 """
#     pid = request.GET.get('id', '')
#     log = Log.objects.filter(pid=pid)
#     if log:
#         log = log[0]
#         dept_name = log.dept_name
#         deptname = get_session_user_info(request)[4]
#         if is_group_admin(request) and dept_name != deptname:
#             return httperror(request, u'Kill失败, 您无权操作!')
#         try:
#             os.kill(int(pid), 9)
#         except OSError:
#             pass
#         Log.objects.filter(pid=pid).update(is_finished=1, end_time=datetime.datetime.now())
#         return render_to_response('jlog/log_offline.html', locals(), context_instance=RequestContext(request))
#     else:
#         return HttpResponseNotFound(u'没有此进程!')


def log_history(request):
    """ 命令历史记录 """
    log_id = request.GET.get('id', 0)
    log = Log.objects.filter(id=log_id)
    if log:
        log = log[0]
        tty_logs = log.ttylog_set.all()

        if tty_logs:
            content = ''
            for tty_log in tty_logs:
                content += '%s: %s\n' % (tty_log.datetime.strftime('%Y-%m-%d %H:%M:%S'), tty_log.cmd)
            return HttpResponse(content)

    return HttpResponse('无日志记录, 请查看日志处理脚本是否开启!')


def log_record(request):
    log_id = request.GET.get('id', 0)
    log = Log.objects.filter(id=int(log_id))
    if log:
        log = log[0]
        log_file = log.log_path + '.log'
        log_time = log.log_path + '.time'
        if os.path.isfile(log_file) and os.path.isfile(log_time):
            content = renderTemplate(log_file, log_time)
            return HttpResponse(content)
        else:
            return HttpResponse('无日志记录, 请查看日志处理脚本是否开启!')


def log_search(request):
    print request.GET
    return render_to_response('jlog/log_filter.html', locals())

# def log_search(request):
#     """ 日志搜索 """
#     offset = request.GET.get('env', '')
#     keyword = request.GET.get('keyword', '')
#     posts = get_user_log(get_user_info(request, offset))
#     contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
#     return render_to_response('jlog/log_search.html', locals(), context_instance=RequestContext(request))
