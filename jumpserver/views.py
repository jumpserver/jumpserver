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
from jumpserver.models import Setting
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from jlog.models import Log
from jperm.perm_api import get_group_user_perm

def getDaysByNum(num):
    """
    输出格式:([datetime.date(2015, 11, 6),  datetime.date(2015, 11, 8)], ['11-06', '11-08'])
    """

    today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    date_li, date_str = [], []
    for i in range(0, num):
        today = today-oneday
        date_li.append(today)
        date_str.append(str(today)[5:10])
    date_li.reverse()
    date_str.reverse()
    return date_li, date_str


def get_data(x, y, z):
    pass


def get_data_by_day(date_li, item):
    data_li = []
    for d in date_li:
        logs = Log.objects.filter(start_time__year=d.year,
                                  start_time__month=d.month,
                                  start_time__day=d.day)
        if item == 'user':
            data_li.append(set([log.user for log in logs]))
        elif item == 'asset':
            data_li.append(set([log.host for log in logs]))
        elif item == 'login':
            data_li.append(logs)
        else:
            pass
    return data_li


def get_count_by_day(date_li, item):
    data_li = get_data_by_day(date_li, item)
    data_count_li = []
    for data in data_li:
        data_count_li.append(len(data))
    return data_count_li


def get_count_by_date(date_li, item):
    data_li = get_data_by_day(date_li, item)
    data_count_tmp = []
    for data in data_li:
        data_count_tmp.extend(list(data))

    return len(set(data_count_tmp))

from jasset.models import Asset, IDC
@require_role(role='user')
def index_cu(request):
    # user_id = request.user.id
    # user = get_object(User, id=user_id)
    login_types = {'L': 'LDAP', 'M': 'MAP'}
    username = request.user.username
    # TODO: need fix,liuzheng need Asset help
    GUP = get_group_user_perm(request.user)
    print GUP
    assets = GUP.get('asset')
    idcs = []
    for i in assets:
        if i.idc_id:
            idcs.append(i.idc_id)
    idc_all = IDC.objects.filter(id__in=idcs)
    for i in idc_all:
        print i.name
    # idc_all = []
    # for i in assets:
    #     idc_all.append(i.idc)
    #     print i.idc.name
    asset_group_all = GUP.get('asset_group')
    # posts = Asset.object.all()
    # host_count = len(posts)
    #
    # new_posts = []
    # post_five = []
    # for post in posts:
    #     if len(post_five) < 5:
    #         post_five.append(post)
    #     else:
    #         new_posts.append(post_five)
    #         post_five = []
    # new_posts.append(post_five)
    return render_to_response('index_cu.html', locals(), context_instance=RequestContext(request))


@require_role(role='user')
def index(request):
    li_date, li_str = getDaysByNum(7)
    today = datetime.datetime.now().day
    from_week = datetime.datetime.now() - datetime.timedelta(days=7)

    if is_role_request(request, 'user'):
        return index_cu(request)

    elif is_role_request(request, 'super'):
        # dashboard 显示汇总
        users = User.objects.all()
        hosts = Asset.objects.all()
        online = Log.objects.filter(is_finished=0)
        online_host = online.values('host').distinct()
        online_user = online.values('user').distinct()
        active_users = User.objects.filter(is_active=1)
        active_hosts = Asset.objects.filter(is_active=1)

        # 一个月历史汇总
        date_li, date_str = getDaysByNum(30)
        date_month = repr(date_str)
        active_user_per_month = str(get_count_by_day(date_li, 'user'))
        active_asset_per_month = str(get_count_by_day(date_li, 'asset'))
        active_login_per_month = str(get_count_by_day(date_li, 'login'))

        # 活跃用户资产图
        active_user_month = get_count_by_date(date_li, 'user')
        disabled_user_count = len(users.filter(is_active=False))
        inactive_user_month = len(users) - active_user_month
        active_asset_month = get_count_by_date(date_li, 'asset')
        disabled_asset_count = len(hosts.filter(is_active=False)) if hosts.filter(is_active=False) else 0
        inactive_asset_month = len(hosts) - active_asset_month if len(hosts) > active_asset_month else 0

        # 一周top10用户和主机
        week_data = Log.objects.filter(start_time__range=[from_week, datetime.datetime.now()])
        user_top_ten = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:10]
        host_top_ten = week_data.values('host').annotate(times=Count('host')).order_by('-times')[:10]

        for user_info in user_top_ten:
            username = user_info.get('user')
            last = Log.objects.filter(user=username).latest('start_time')
            user_info['last'] = last

        for host_info in host_top_ten:
            host = host_info.get('host')
            last = Log.objects.filter(host=host).latest('start_time')
            host_info['last'] = last

        # 一周top5
        week_users = week_data.values('user').distinct().count()
        week_hosts = week_data.count()

        user_top_five = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:5]
        color = ['label-success', 'label-info', 'label-primary', 'label-default', 'label-warnning']

        # 最后10次权限申请
        # perm apply latest 10
        # perm_apply_10 = Apply.objects.order_by('-date_add')[:10]

        # 最后10次登陆
        login_10 = Log.objects.order_by('-start_time')[:10]
        login_more_10 = Log.objects.order_by('-start_time')[10:21]

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
    error = ''
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    if request.method == 'GET':
        return render_to_response('login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        if username and password:
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    # c = {}
                    # c.update(csrf(request))
                    # request.session['csrf_token'] = str(c.get('csrf_token'))
        # user_filter = User.objects.filter(username=username)
        # if user_filter:
        #     user = user_filter[0]
        #     if PyCrypt.md5_crypt(password) == user.password:
        #         request.session['user_id'] = user.id
        #         user_filter.update(last_login=datetime.datetime.now())
                    if user.role == 'SU':
                        request.session['role_id'] = 2
                    elif user.role == 'GA':
                        request.session['role_id'] = 1
                    else:
                        request.session['role_id'] = 0
                    return HttpResponseRedirect(request.session.get('pre_url', '/'))
                # response.set_cookie('username', username, expires=604800)
                # response.set_cookie('seed', PyCrypt.md5_crypt(password), expires=604800)
                # return response
                else:
                    error = '用户未激活'
            else:
                error = '用户名或密码错误'
        else:
            error = '用户名或密码错误'
    return render_to_response('login.html', {'error': error})


def Logout(request):
    logout(request)
    return HttpResponseRedirect('/login/')


def setting(request):
    header_title, path1 = '项目设置', '设置'
    setting_default = get_object(Setting, name='default')

    if request.method == "POST":
        setting_raw = request.POST.get('setting', '')
        if setting_raw == 'default':
            username = request.POST.get('username', '')
            port = request.POST.get('port', '')
            password = request.POST.get('password', '')
            private_key = request.POST.get('key', '')

            if '' in [username, port] and ('' in password or '' in private_key):
                return HttpResponse('所填内容不能为空, 且密码和私钥填一个')
            else:
                private_key_path = os.path.join(BASE_DIR, 'keys/role_keys', 'default', 'default_private_key.pem')
                if private_key:
                    with open(private_key_path, 'w') as f:
                            f.write(private_key)
                    os.chmod(private_key_path, 0600)

                if setting_default:
                    if password != setting_default.default_password:
                        password_encode = CRYPTOR.encrypt(password)
                    else:
                        password_encode = password
                    Setting.objects.filter(name='default').update(default_user=username, default_port=port,
                                                                  default_password=password_encode,
                                                                  default_pri_key_path=private_key_path)

                else:
                    password_encode = CRYPTOR.encrypt(password)
                    setting_r = Setting(name='default', default_user=username, default_port=port,
                                        default_password=password_encode,
                                        default_pri_key_path=private_key_path).save()

            msg = "设置成功"
    return my_render('setting.html', locals(), request)


def test2(request):
    return my_render('test2.html', locals(), request)
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


#######################  liuzheng's  test(start) ########################
from django.contrib.auth.decorators import login_required
from juser.models import Document

@login_required(login_url='/login')
def upload(request):
    if request.method == 'GET':
        machines = [{'name':'aaa'}]
        return render_to_response('upload.html', locals(), context_instance=RequestContext(request))
    elif request.method == 'POST':
        upload_files = request.FILES.getlist('file[]', None)
        for file in upload_files:
            print file
            newdoc = Document(docfile=file, user_id=request.user.id)
            newdoc.save()
        return HttpResponse("success")
    else:
        return HttpResponse("ERROR")

@login_required(login_url='/login')
def download(request):
    documents = []
    for doc in Document.objects.filter(user_id=request.user.id).all():
        documents.append('/'.join(str(doc.docfile).split('/')[2:]))
    return render_to_response('download.html', locals(), context_instance=RequestContext(request))

def download_file(request, path):
    # TODO: get downlode file and make sure it is exist!
    # by liuzheng
    filepath = 'upload/' + str(request.user.id)+'/'+path
    return HttpResponse(filepath)

def node_auth(request):
    return HttpResponse('nothing')
def httperror(request):
    return HttpResponse('nothing')
def base(request):
    return HttpResponse('nothing')
def install(request):
    return HttpResponse('nothing')

#######################  liuzheng's  test(end) ########################