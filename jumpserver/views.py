# coding: utf-8

from __future__ import division
import uuid
import urllib

from django.db.models import Count
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseNotFound
from django.http import HttpResponse
# from jperm.models import Apply
import paramiko
from jumpserver.api import *
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from settings import BASE_DIR

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

class CustomUser(object):
    def __init__(self,request):
        self.requset = request

    def __unicode__(self):
        return self.requset.user.username

    def get_asset_group(self):
        """
        Get user host_groups.
        获取用户有权限的主机组
        """
        host_group_list = []
        perm_list = []
        user_group_all = self.requset.user.group.all()
        for user_group in user_group_all:
            perm_list.extend(user_group.perm_set.all())

        for perm in perm_list:
            host_group_list.append(perm.asset_group)

        return host_group_list

    def get_asset_group_info(self, printable=False):
        """
        Get or print asset group info
        获取或打印用户授权资产组
        """
        asset_groups_info = {}
        asset_groups = self.get_asset_group()

        for asset_group in asset_groups:
            asset_groups_info[asset_group.id] = [asset_group.name, asset_group.comment]

        if printable:
            for group_id in asset_groups_info:
                if asset_groups_info[group_id][1]:
                    print "[%3s] %s -- %s" % (group_id,
                                              asset_groups_info[group_id][0],
                                              asset_groups_info[group_id][1])
                else:
                    print "[%3s] %s" % (group_id, asset_groups_info[group_id][0])
                print ''
        else:
            return asset_groups_info

    def get_asset(self):
        """
        Get the assets of under the user control.
        获取主机列表
        """
        assets = []
        asset_groups = self.get_asset_group()

        for asset_group in asset_groups:
            assets.extend(asset_group.asset_set.all())

        return assets

    def get_asset_info(self, printable=False):
        """
        Get or print the user asset info
        获取或打印用户资产信息
        """
        from jasset.models import AssetAlias
        assets_info = {}
        assets = self.get_asset()

        for asset in assets:
            asset_alias = AssetAlias.objects.filter(user=self, asset=asset)
            if asset_alias and asset_alias[0].alias != '':
                assets_info[asset.ip] = [asset.id, asset.ip, str(asset_alias[0].alias)]
            else:
                assets_info[asset.ip] = [asset.id, asset.ip, str(asset.comment)]

        if printable:
            ips = assets_info.keys()
            ips.sort()
            for ip in ips:
                if assets_info[ip][2]:
                    print '%-15s -- %s' % (ip, assets_info[ip][2])
                else:
                    print '%-15s' % ip
            print ''
        else:
            return assets_info


# @login_required
@require_role(role='user')
def index_cu(request):
    # user_id = request.session.get('user_id')
    # user = get_object(User, id=user_id)
    # user = {}
    # user.name = request.user.username
    # user.username = request.user.username
    # user.id = request.user.id
    login_types = {'L': 'LDAP', 'M': 'MAP'}
    user = CustomUser(request)
    posts = user.get_asset()
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


@require_role(role='user')
def index(request):
    li_date, li_str = getDaysByNum(7)
    today = datetime.datetime.now().day
    from_week = datetime.datetime.now() - datetime.timedelta(days=7)

    if is_role_request(request, 'user'):
        return index_cu(request)

    elif is_role_request(request, 'super'):
        users = User.objects.all()
        hosts = Asset.objects.all()
        online = Log.objects.filter(is_finished=0)
        online_host = online.values('host').distinct()
        online_user = online.values('user').distinct()
        active_users = User.objects.filter(is_active=1)
        active_hosts = Asset.objects.filter(is_active=1)
        week_data = Log.objects.filter(start_time__range=[from_week, datetime.datetime.now()])

    elif is_role_request(request, 'admin'):
        return index_cu(request)
        # user = get_session_user_info(request)[2]
        # users = User.objects.filter(dept=dept)
        # hosts = Asset.objects.filter(dept=dept)
        # online = Log.objects.filter(dept_name=dept_name, is_finished=0)
        # online_host = online.values('host').distinct()
        # online_user = online.values('user').distinct()
        # active_users = users.filter(is_active=1)
        # active_hosts = hosts.filter(is_active=1)
        # week_data = Log.objects.filter(dept_name=dept_name, start_time__range=[from_week, datetime.datetime.now()])

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

    user_top_ten = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:10]
    host_top_ten = week_data.values('host').annotate(times=Count('host')).order_by('-times')[:10]
    user_dic, host_dic = get_data(week_data, user_top_ten, 'user'), get_data(week_data, host_top_ten, 'host')

    # a week data
    week_users = week_data.values('user').distinct().count()
    week_hosts = week_data.count()

    user_top_five = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:5]
    color = ['label-success', 'label-info', 'label-primary', 'label-default', 'label-warnning']

    # perm apply latest 10
    # perm_apply_10 = Apply.objects.order_by('-date_add')[:10]

    # latest 10 login
    login_10 = Log.objects.order_by('-start_time')[:10]
    login_more_10 = Log.objects.order_by('-start_time')[10:21]

    # a week top 10
    for user_info in user_top_ten:
        username = user_info.get('user')
        last = Log.objects.filter(user=username).latest('start_time')
        user_info['last'] = last

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


# def pages(posts, r):
#     """分页公用函数"""
#     contact_list = posts
#     p = paginator = Paginator(contact_list, 10)
#     try:
#         current_page = int(r.GET.get('page', '1'))
#     except ValueError:
#         current_page = 1
#
#     page_range = page_list_return(len(p.page_range), current_page)
#
#     try:
#         contacts = paginator.page(current_page)
#     except (EmptyPage, InvalidPage):
#         contacts = paginator.page(paginator.num_pages)
#
#     if current_page >= 5:
#         show_first = 1
#     else:
#         show_first = 0
#     if current_page <= (len(p.page_range) - 3):
#         show_end = 1
#     else:
#         show_end = 0
#
#     return contact_list, p, contacts, page_range, current_page, show_first, show_end


def is_latest():
    node = uuid.getnode()
    jsn = uuid.UUID(int=node).hex[-12:]
    with open(os.path.join(BASE_DIR, 'version')) as f:
        current_version = f.read()
    lastest_version = urllib.urlopen('http://www.jumpserver.org/lastest_version.html?jsn=%s' % jsn).read().strip()

    if current_version != lastest_version:
        pass


def Login(request):
    """登录界面"""
    if request.session.get('username'):
        return HttpResponseRedirect('/')
    if request.method == 'GET':
        return render_to_response('login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                request.session['user_id'] = user.id
                if user.role == 'SU':
                    request.session['role_id'] = 2
                elif user.role == 'GA':
                    request.session['role_id'] = 1
                else:
                    request.session['role_id'] = 0
                # response.set_cookie('username', username, expires=604800)
                # response.set_cookie('seed', PyCrypt.md5_crypt(password), expires=604800)
                return HttpResponseRedirect('/', )
            else:
                error = '密码错误，请重新输入。'
        else:
            error = '用户不存在。'
    return render_to_response('login.html', {'error': error})


def Logout(request):
    logout(request)
    return HttpResponseRedirect('/login/')

#
# def filter_ajax_api(request):
#     attr = request.GET.get('attr', 'user')
#     value = request.GET.get('value', '')
#     if attr == 'user':
#         contact_list = User.objects.filter(name__icontains=value)
#     elif attr == "user_group":
#         contact_list = UserGroup.objects.filter(name__icontains=value)
#     elif attr == "asset":
#         contact_list = Asset.objects.filter(ip__icontains=value)
#     elif attr == "asset":
#         contact_list = BisGroup.objects.filter(name__icontains=value)
#
#     return render_to_response('filter_ajax_api.html', locals())
#
#
# def install(request):
#     from juser.models import DEPT, User
#     if User.objects.filter(id=5000):
#         return http_error(request, 'Jumpserver已初始化，不能重复安装！')
#
#     dept = DEPT(id=1, name="超管部", comment="超级管理部门")
#     dept.save()
#     dept2 = DEPT(id=2, name="默认", comment="默认部门")
#     dept2.save()
#     IDC(id=1, name="默认", comment="默认IDC").save()
#     BisGroup(id=1, name="ALL", dept=dept, comment="所有主机组").save()
#
#     User(id=5000, username="admin", password=PyCrypt.md5_crypt('admin'),
#          name='admin', email='admin@jumpserver.org', role='SU', is_active=True, dept=dept).save()
#     return http_success(request, u'Jumpserver初始化成功')
#
#
# def download(request):
#     return render_to_response('download.html', locals(), context_instance=RequestContext(request))
#
#
# def transfer(sftp, filenames):
#     # pool = Pool(processes=5)
#     for filename, file_path in filenames.items():
#         print filename, file_path
#         sftp.put(file_path, '/tmp/%s' % filename)
#         # pool.apply_async(transfer, (sftp, file_path, '/tmp/%s' % filename))
#     sftp.close()
#     # pool.close()
#     # pool.join()
#
#
# def upload(request):
#     pass
# #     user, dept = get_session_user_dept(request)
# #     if request.method == 'POST':
# #         hosts = request.POST.get('hosts')
# #         upload_files = request.FILES.getlist('file[]', None)
# #         upload_dir = "/tmp/%s" % user.username
# #         is_dir(upload_dir)
# #         date_now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
# #         hosts_list = hosts.split(',')
# #         user_hosts = [asset.ip for asset in user.get_asset()]
# #         unperm_hosts = []
# #         filenames = {}
# #         for ip in hosts_list:
# #             if ip not in user_hosts:
# #                 unperm_hosts.append(ip)
# #
# #         if not hosts:
# #             return HttpResponseNotFound(u'地址不能为空')
# #
# #         if unperm_hosts:
# #             print hosts_list
# #             return HttpResponseNotFound(u'%s 没有权限.' % ', '.join(unperm_hosts))
# #
# #         for upload_file in upload_files:
# #             file_path = '%s/%s.%s' % (upload_dir, upload_file.name, date_now)
# #             filenames[upload_file.name] = file_path
# #             f = open(file_path, 'w')
# #             for chunk in upload_file.chunks():
# #                 f.write(chunk)
# #             f.close()
# #
# #         sftps = []
# #         for host in hosts_list:
# #             username, password, host, port = get_connect_item(user.username, host)
# #             try:
# #                 t = paramiko.Transport((host, port))
# #                 t.connect(username=username, password=password)
# #                 sftp = paramiko.SFTPClient.from_transport(t)
# #                 sftps.append(sftp)
# #             except paramiko.AuthenticationException:
# #                 return HttpResponseNotFound(u'%s 连接失败.' % host)
# #
# #         # pool = Pool(processes=5)
# #         for sftp in sftps:
# #             transfer(sftp, filenames)
# #         # pool.close()
# #         # pool.join()
# #         return HttpResponse('传送成功')
# #
# #     return render_to_response('upload.html', locals(), context_instance=RequestContext(request))
#
#
# def node_auth(request):
#     username = request.POST.get('username', ' ')
#     seed = request.POST.get('seed', ' ')
#     filename = request.POST.get('filename', ' ')
#     user = User.objects.filter(username=username, password=seed)
#     auth = 1
#     if not user:
#         auth = 0
#     if not filename.startswith('/opt/jumpserver/logs/connect/'):
#         auth = 0
#     if auth:
#         result = {'auth': {'username': username, 'result': 'success'}}
#     else:
#         result = {'auth': {'username': username, 'result': 'failed'}}
#
#     return HttpResponse(json.dumps(result, sort_keys=True, indent=2), content_type='application/json')
