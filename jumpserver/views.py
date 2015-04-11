# coding: utf-8

from __future__ import division
from django.db.models import Count
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseNotFound
from jperm.models import Apply
import paramiko
from jumpserver.api import *


def getDaysByNum(num):
    today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    li_date, li_str = [], []
    for i in range(0, num):
        today = today-oneday
        li_date.append(today)
        li_str.append(str(today)[5:10])
    li_date.reverse()
    li_str.reverse()
    t = (li_date, li_str)
    return t


def get_data(data, items, option):
    dic = {}
    li_date, li_str = getDaysByNum(7)
    for item in items:
        li = []
        name = item[option]
        if option == 'user':
            option_data = data.filter(user=name)
        elif option == 'host':
            option_data = data.filter(host=name)
        for t in li_date:
            year, month, day = t.year, t.month, t.day
            times = option_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).count()
            li.append(times)
        dic[name] = li
    return dic


@require_login
def index_cu(request):
    user_id = request.session.get('user_id')
    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
    login_types = {'L': 'LDAP', 'M': 'MAP'}
    user_id = request.session.get('user_id')
    username = User.objects.get(id=user_id).name
    posts = user_perm_asset_api(username)
    host_count = len(posts)
    new_posts = []
    post_five = []
    for post in posts:
        if len(post_five) < 5:
            post_five.append(post)
        else:
            new_posts.append(post_five)
            post_five = []
    new_posts.append(post_five)

    return render_to_response('index_cu.html', locals(), context_instance=RequestContext(request))


@require_admin
def admin_index(request):
    user_id = request.session.get('user_id', '')
    user = User.objects.get(id=user_id)
    dept = user.dept
    dept_name = user.dept.name
    users = User.objects.filter(dept=dept)
    hosts = Asset.objects.filter(dept=dept)
    online = Log.objects.filter(dept_name=dept_name, is_finished=0)
    online_host = online.values('host').distinct()
    online_user = online.values('user').distinct()
    active_users = users.filter(is_active=1)
    active_hosts = hosts.filter(is_active=1)

    # percent of dashboard
    percent_user = format(active_users.count() / users.count(), '.0%')
    percent_host = format(active_hosts.count() / hosts.count(), '.0%')
    percent_online_user = format(online_user.count() / users.count(), '.0%')
    percent_online_host = format(online_host.count() / hosts.count(), '.0%')

    li_date, li_str = getDaysByNum(7)
    today = datetime.datetime.now().day
    from_week = datetime.datetime.now() - datetime.timedelta(days=7)
    week_data = Log.objects.filter(dept_name=dept_name, start_time__range=[from_week, datetime.datetime.now()])
    user_top_ten = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:10]
    host_top_ten = week_data.values('host').annotate(times=Count('host')).order_by('-times')[:10]
    user_dic, host_dic = get_data(week_data, user_top_ten, 'user'), get_data(week_data, host_top_ten, 'host')

    # a week data
    week_users = week_data.values('user').distinct().count()
    week_hosts = week_data.count()

    user_top_five = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:5]
    color = ['label-success', 'label-info', 'label-primary', 'label-default', 'label-warnning']

    # perm apply latest 10
    perm_apply_10 = Apply.objects.order_by('-date_add')[:10]

    # latest 10 login
    login_10 = Log.objects.order_by('-start_time')[:10]
    login_more_10 = Log.objects.order_by('-start_time')[10:21]

    # a week top 10
    for user_info in user_top_ten:
        username = user_info.get('user')
        last = Log.objects.filter(user=username).latest('start_time')
        user_info['last'] = last
    print user_top_ten

    top = {'user': '活跃用户数', 'host': '活跃主机数', 'times': '登录次数'}
    top_dic = {}
    for key, value in top.items():
        li = []
        for t in li_date:
            year, month, day = t.year, t.month, t.day
            if key != 'times':
                times = week_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).values(key).distinct().count()
            else:
                times = week_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).count()
            li.append(times)
        top_dic[value] = li
    return render_to_response('index.html', locals(), context_instance=RequestContext(request))


@require_login
def index(request):
    if is_common_user(request):
        return index_cu(request)

    if is_group_admin(request):
        return admin_index(request)
    users = User.objects.all()
    hosts = Asset.objects.all()
    online = Log.objects.filter(is_finished=0)
    online_host = online.values('host').distinct()
    online_user = online.values('user').distinct()
    active_users = User.objects.filter(is_active=1)
    active_hosts = Asset.objects.filter(is_active=1)

    # percent of dashboard
    if users.count() == 0:
        percent_user, percent_online_user = '0%', '0%'
    else:
        percent_user = format(active_users.count() / users.count(), '.0%')
        percent_online_user = format(online_user.count() / users.count(), '.0%')
    if hosts.count() == 0:
        percent_host, percent_online_host = '0%', '0%'
    else:
        percent_host = format(active_hosts.count() / hosts.count(), '.0%')
        percent_online_host = format(online_host.count() / hosts.count(), '.0%')

    li_date, li_str = getDaysByNum(7)
    today = datetime.datetime.now().day
    from_week = datetime.datetime.now() - datetime.timedelta(days=7)
    week_data = Log.objects.filter(start_time__range=[from_week, datetime.datetime.now()])
    user_top_ten = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:10]
    host_top_ten = week_data.values('host').annotate(times=Count('host')).order_by('-times')[:10]
    user_dic, host_dic = get_data(week_data, user_top_ten, 'user'), get_data(week_data, host_top_ten, 'host')

    # a week data
    week_users = week_data.values('user').distinct().count()
    week_hosts = week_data.count()

    user_top_five = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:5]
    color = ['label-success', 'label-info', 'label-primary', 'label-default', 'label-warnning']

    # perm apply latest 10
    perm_apply_10 = Apply.objects.order_by('-date_add')[:10]
    login_more_10 = Log.objects.order_by('-start_time')[10:20]

    # latest 10 login
    login_10 = Log.objects.order_by('-start_time')[:10]

    # a week top 10
    for user_info in user_top_ten:
        username = user_info.get('user')
        last = Log.objects.filter(user=username).latest('start_time')
        user_info['last'] = last
    print user_top_ten

    top = {'user': '活跃用户数', 'host': '活跃主机数', 'times': '登录次数'}
    top_dic = {}
    for key, value in top.items():
        li = []
        for t in li_date:
            year, month, day = t.year, t.month, t.day
            if key != 'times':
                times = week_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).values(key).distinct().count()
            else:
                times = week_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).count()
            li.append(times)
        top_dic[value] = li
    return render_to_response('index.html', locals(), context_instance=RequestContext(request))


def skin_config(request):
    return render_to_response('skin_config.html')


def pages(posts, r):
    """分页公用函数"""
    contact_list = posts
    p = paginator = Paginator(contact_list, 10)
    try:
        current_page = int(r.GET.get('page', '1'))
    except ValueError:
        current_page = 1

    page_range = page_list_return(len(p.page_range), current_page)

    try:
        contacts = paginator.page(current_page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)

    if current_page >= 5:
        show_first = 1
    else:
        show_first = 0
    if current_page <= (len(p.page_range) - 3):
        show_end = 1
    else:
        show_end = 0

    return contact_list, p, contacts, page_range, current_page, show_first, show_end


def login(request):
    """登录界面"""
    if request.session.get('username'):
        return HttpResponseRedirect('/')
    if request.method == 'GET':
        return render_to_response('login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = User.objects.filter(username=username)
        if user:
            user = user[0]
            if md5_crypt(password) == user.password:
                request.session['user_id'] = user.id
                if user.role == 'SU':
                    request.session['role_id'] = 2
                elif user.role == 'DA':
                    request.session['role_id'] = 1
                else:
                    request.session['role_id'] = 0
                return HttpResponseRedirect('/')
            else:
                error = '密码错误，请重新输入。'
        else:
            error = '用户不存在。'
    return render_to_response('login.html', {'error': error})


def logout(request):
    request.session.delete()
    return HttpResponseRedirect('/login/')


def filter_ajax_api(request):
    attr = request.GET.get('attr', 'user')
    value = request.GET.get('value', '')
    if attr == 'user':
        contact_list = User.objects.filter(name__icontains=value)
    elif attr == "user_group":
        contact_list = UserGroup.objects.filter(name__icontains=value)
    elif attr == "asset":
        contact_list = Asset.objects.filter(ip__icontains=value)
    elif attr == "asset":
        contact_list = BisGroup.objects.filter(name__icontains=value)

    return render_to_response('filter_ajax_api.html', locals())


def install(request):
    from juser.models import DEPT, User
    dept = DEPT(id=1, name="超管部", comment="SUPER DEPT")
    dept.save()
    dept2 = DEPT(id=2, name="默认", comment="DEFAULT DEPT")
    dept2.save()
    IDC(id=1, name="默认", comment="DEFAULT IDC").save()
    BisGroup(id=1, name="ALL", dept=dept, comment="ALL USER GROUP").save()

    User(id=5000, username="admin", password=md5_crypt('admin'),
         name='admin', email='admin@jumpserver.org', role='SU', is_active=True, dept=dept).save()
    User(id=5001, username="group_admin", password=md5_crypt('group_admin'),
         name='group_admin', email='group_admin@jumpserver.org', role='DA', is_active=True, dept=dept2).save()
    return HttpResponse('Ok')


def download(request):
    return render_to_response('download.html', locals(), context_instance=RequestContext(request))


def transfer(sftp, filenames):
    # pool = Pool(processes=5)
    for filename, file_path in filenames.items():
        print filename, file_path
        sftp.put(file_path, '/tmp/%s' % filename)
        # pool.apply_async(transfer, (sftp, file_path, '/tmp/%s' % filename))
    sftp.close()
    # pool.close()
    # pool.join()


def upload(request):
    user, dept = get_session_user_dept(request)
    if request.method == 'POST':
        hosts = request.POST.get('hosts')
        upload_files = request.FILES.getlist('file[]', None)
        upload_dir = "/tmp/%s" % user.username
        is_dir(upload_dir)
        date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        hosts_list = hosts.split(',')
        user_hosts = get_user_host(user.username).keys()
        unperm_hosts = []
        filenames = {}
        for ip in hosts_list:
            if ip not in user_hosts:
                unperm_hosts.append(ip)

        if not hosts:
            return HttpResponseNotFound(u'地址不能为空')

        if unperm_hosts:
            print hosts_list
            return HttpResponseNotFound(u'%s 没有权限.' % ', '.join(unperm_hosts))

        for upload_file in upload_files:
            file_path = '%s/%s.%s' % (upload_dir, upload_file.name, date_now)
            filenames[upload_file.name] = file_path
            f = open(file_path, 'w')
            for chunk in upload_file.chunks():
                f.write(chunk)
            f.close()

        sftps = []
        for host in hosts_list:
            username, password, host, port = get_connect_item(user.username, host)
            try:
                t = paramiko.Transport((host, port))
                t.connect(username=username, password=password)
                sftp = paramiko.SFTPClient.from_transport(t)
                sftps.append(sftp)
            except paramiko.AuthenticationException:
                return HttpResponseNotFound(u'%s 连接失败.' % host)

        # pool = Pool(processes=5)
        for sftp in sftps:
            transfer(sftp, filenames)
        # pool.close()
        # pool.join()
        return HttpResponse('传送成功')

    return render_to_response('upload.html', locals(), context_instance=RequestContext(request))
