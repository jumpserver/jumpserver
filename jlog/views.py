# coding:utf-8
from django.db.models import Q
from django.template import RequestContext
from django.shortcuts import render_to_response

from jumpserver.api import *
from jperm.perm_api import user_have_perm
from django.http import HttpResponseNotFound
from jlog.log_api import renderTemplate

from jlog.models import Log, ExecLog, FileLog


@require_role('admin')
def log_list(request, offset):
    """ 显示日志 """
    header_title, path1 = u'审计', u'操作审计'
    date_seven_day = request.GET.get('start', '')
    date_now_str = request.GET.get('end', '')
    username_list = request.GET.getlist('username', [])
    host_list = request.GET.getlist('host', [])
    cmd = request.GET.get('cmd', '')

    if offset == 'online':
        keyword = request.GET.get('keyword', '')
        posts = Log.objects.filter(is_finished=False).order_by('-start_time')
        if keyword:
            posts = posts.filter(Q(user__icontains=keyword) | Q(host__icontains=keyword) |
                                 Q(login_type_icontains=keyword))

    elif offset == 'exec':
        posts = ExecLog.objects.all().order_by('-id')
        keyword = request.GET.get('keyword', '')
        if keyword:
            posts = posts.filter(Q(user__icontains=keyword)|Q(host__icontains=keyword)|Q(cmd__icontains=keyword))
    elif offset == 'file':
        posts = FileLog.objects.all().order_by('-id')
        keyword = request.GET.get('keyword', '')
        if keyword:
            posts = posts.filter(Q(user__icontains=keyword)|Q(host__icontains=keyword)|Q(filename__icontains=keyword))
    else:
        posts = Log.objects.filter(is_finished=True).order_by('-start_time')
        username_all = set([log.user for log in Log.objects.all()])
        ip_all = set([log.host for log in Log.objects.all()])

        if date_seven_day and date_now_str:
            datetime_start = datetime.datetime.strptime(date_seven_day + ' 00:00:01', '%m/%d/%Y %H:%M:%S')
            datetime_end = datetime.datetime.strptime(date_now_str + ' 23:59:59', '%m/%d/%Y %H:%M:%S')
            posts = posts.filter(start_time__gte=datetime_start).filter(start_time__lte=datetime_end)

        if username_list:
            posts = posts.filter(user__in=username_list)

        if host_list:
            posts = posts.filter(host__in=host_list)

        if cmd:
            log_id_list = set([log.log_id for log in TtyLog.objects.filter(cmd__contains=cmd)])
            posts = posts.filter(id__in=log_id_list)

        if not date_seven_day:
            date_now = datetime.datetime.now()
            date_now_str = date_now.strftime('%m/%d/%Y')
            date_seven_day = (date_now + datetime.timedelta(days=-7)).strftime('%m/%d/%Y')

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    session_id = request.session.session_key
    return render_to_response('jlog/log_%s.html' % offset, locals(), context_instance=RequestContext(request))


@require_role('admin')
def log_detail(request):
    return my_render('jlog/exec_detail.html', locals(), request)


@require_role('admin')
def log_kill(request):
    """ 杀掉connect进程 """
    pid = request.GET.get('id', '')
    log = Log.objects.filter(pid=pid)
    if log:
        log = log[0]
        try:
            os.kill(int(pid), 9)
        except OSError:
            pass
        Log.objects.filter(pid=pid).update(is_finished=1, end_time=datetime.datetime.now())
        return render_to_response('jlog/log_offline.html', locals(), context_instance=RequestContext(request))
    else:
        return HttpResponseNotFound(u'没有此进程!')


@require_role('admin')
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

    return HttpResponse('无日志记录!')


@require_role('admin')
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
            return HttpResponse('无日志记录!')


@require_role('admin')
def log_detail(request, offset):
    log_id = request.GET.get('id')
    if offset == 'exec':
        log = get_object(ExecLog, id=log_id)
        assets_hostname = log.host.split(' ')
        try:
            result = eval(str(log.result))
        except (SyntaxError, NameError):
            result = {}
        return my_render('jlog/exec_detail.html', locals(), request)
    elif offset == 'file':
        log = get_object(FileLog, id=log_id)
        assets_hostname = log.host.split(' ')
        file_list = log.filename.split(' ')
        try:
            result = eval(str(log.result))
        except (SyntaxError, NameError):
            result = {}
        return my_render('jlog/file_detail.html', locals(), request)
