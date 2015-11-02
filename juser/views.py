# coding: utf-8
# Author: Guanghongwei
# Email: ibuler@qq.com

# import random
# from Crypto.PublicKey import RSA
import uuid as uuid_r
from django.contrib.auth.decorators import login_required

from django.db.models import Q
from django.template import RequestContext
from django.db.models import ObjectDoesNotExist
from jumpserver.settings import MAIL_FROM, MAIL_ENABLE
from juser.user_api import *


def chg_role(request):
    role = {'SU': 2, 'GA': 1, 'CU': 0}
    if request.session['role_id'] > 0:
        request.session['role_id'] = 0
    elif request.session['role_id'] == 0:
        request.session['role_id'] = role.get(request.user.role, 0)
    return HttpResponseRedirect('/')


@require_role(role='super')
def group_add(request):
    """
    group add view for route
    添加用户组的视图
    """
    error = ''
    msg = ''
    header_title, path1, path2 = '添加用户组', '用户管理', '添加用户组'
    user_all = User.objects.all()

    if request.method == 'POST':
        group_name = request.POST.get('group_name', '')
        users_selected = request.POST.getlist('users_selected', '')
        comment = request.POST.get('comment', '')

        try:
            if not group_name:
                error = u'组名 不能为空'
                raise ServerError(error)

            if UserGroup.objects.filter(name=group_name):
                error = u'组名已存在'
                raise ServerError(error)
            db_add_group(name=group_name, users_id=users_selected, comment=comment)
        except ServerError:
            pass
        except TypeError:
            error = u'添加小组失败'
        else:
            msg = u'添加组 %s 成功' % group_name

    return my_render('juser/group_add.html', locals(), request)


@require_role(role='super')
def group_list(request):
    """
    list user group
    用户组列表
    """
    header_title, path1, path2 = '查看用户组', '用户管理', '查看用户组'
    keyword = request.GET.get('search', '')
    user_group_list = UserGroup.objects.all().order_by('name')

    if keyword:
        user_group_list = user_group_list.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))

    user_group_list, p, user_groups, page_range, current_page, show_first, show_end = pages(user_group_list, request)
    return my_render('juser/group_list.html', locals(), request)


@require_role(role='super')
def group_del(request):
    """
    del a group
    删除用户组
    """
    group_ids = request.GET.get('id', '')
    group_id_list = group_ids.split(',')
    for group_id in group_id_list:
        UserGroup.objects.filter(id=group_id).delete()

    return HttpResponse('删除成功')


# @require_role(role='admin')
# def group_list_adm(request):
#     header_title, path1, path2 = '查看部门小组', '用户管理', '查看小组'
#     keyword = request.GET.get('search', '')
#     did = request.GET.get('did', '')
#     user, dept = get_session_user_dept(request)
#     contact_list = dept.usergroup_set.all().order_by('name')
#
#     if keyword:
#         contact_list = contact_list.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))
#
#     contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)
#     return render_to_response('juser/group_list.html', locals(), context_instance=RequestContext(request))

#
# @require_role(role='admin')
# def group_detail(request):
#     group_id = request.GET.get('id', None)
#     if not group_id:
#         return HttpResponseRedirect('/')
#     group = UserGroup.objects.get(id=group_id)
#     users = group.user_set.all()
#     return render_to_response('juser/group_detail.html', locals(), context_instance=RequestContext(request))


@require_role(role='super')
def group_edit(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '编辑用户组', '用户管理', '编辑用户组'

    if request.method == 'GET':
        group_id = request.GET.get('id', '')
        user_group = get_object(UserGroup, id=group_id)
        if user_group:
            users_all = User.objects.all()
            users_selected = user_group.user_set.all()
            users_remain = [user for user in users_all if user not in users_selected]

    else:
        group_id = request.POST.get('group_id', '')
        group_name = request.POST.get('group_name', '')
        comment = request.POST.get('comment', '')
        users_selected = request.POST.getlist('users_selected')

        users = []
        try:
            if '' in [group_id, group_name]:
                raise ServerError('组名不能为空')

            user_group = get_object(UserGroup, id=group_id)
            other_group = get_object(UserGroup, name=group_name)

            if other_group and other_group.id != int(group_id):
                raise ServerError(u'%s 用户组已存在' % group_name)

            for user_id in users_selected:
                users.extend(User.objects.filter(id=user_id))

            if user_group:
                user_group.update(name=group_name, comment=comment)
                user_group.user_set.clear()
                user_group.user_set = users

        except ServerError, e:
            error = e
        if not error:
            return HttpResponseRedirect('/juser/group_list/')
        else:
            users_all = User.objects.all()
            users_selected = user_group.user_set.all()
            users_remain = [user for user in users_all if user not in users_selected]

    return my_render('juser/group_edit.html', locals(), request)


# @require_role(role='admin')
# def group_edit_adm(request):
#     error = ''
#     msg = ''
#     header_title, path1, path2 = '修改小组信息', '用户管理', '编辑小组'
#     user, dept = get_session_user_dept(request)
#     if request.method == 'GET':
#         group_id = request.GET.get('id', '')
#         if not validate(request, user_group=[group_id]):
#             return HttpResponseRedirect('/juser/group_list/')
#         group = UserGroup.objects.filter(id=group_id)
#         if group:
#             group = group[0]
#             users_all = dept.user_set.all()
#             users_selected = group.user_set.all()
#             users = [user for user in users_all if user not in users_selected]
#
#         return render_to_response('juser/group_edit.html', locals(), context_instance=RequestContext(request))
#     else:
#         group_id = request.POST.get('group_id', '')
#         group_name = request.POST.get('group_name', '')
#         comment = request.POST.get('comment', '')
#         users_selected = request.POST.getlist('users_selected')
#
#         users = []
#         try:
#             if not validate(request, user=users_selected):
#                 raise ServerError(u'右侧非部门用户')
#
#             if not validate(request, user_group=[group_id]):
#                 raise ServerError(u'没有权限修改本组')
#
#             for user_id in users_selected:
#                 users.extend(User.objects.filter(id=user_id))
#
#             user_group = UserGroup.objects.filter(id=group_id)
#             if user_group:
#                 user_group.update(name=group_name, comment=comment, dept=dept)
#                 user_group = user_group[0]
#                 user_group.user_set.clear()
#                 user_group.user_set = users
#
#         except ServerError, e:
#             error = e
#
#         return HttpResponseRedirect('/juser/group_list/')


@login_required(login_url='/login')
@require_role(role='super')
def user_add(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '添加用户', '用户管理', '添加用户'
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    group_all = UserGroup.objects.all()

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = PyCrypt.random_pass(16)
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        groups = request.POST.getlist('groups', [])
        admin_groups = request.POST.getlist('admin_groups', [])
        role = request.POST.get('role', 'CU')
        uuid = uuid_r.uuid1()
        ssh_key_pwd = PyCrypt.random_pass(16)
        extra = request.POST.getlist('extra', [])
        is_active = True if '0' in extra else False
        ssh_key_login_need = True if '1' in extra else False
        send_mail_need = True if '2' in extra else False

        try:
            if '' in [username, password, ssh_key_pwd, name, role]:
                error = u'带*内容不能为空'
                raise ServerError
            check_user_is_exist = User.objects.filter(username=username)
            if check_user_is_exist:
                error = u'用户 %s 已存在' % username
                raise ServerError

        except ServerError:
            pass
        else:
            try:
                user = db_add_user(username=username, name=name,
                                   password=password,
                                   email=email, role=role, uuid=uuid,
                                   groups=groups, admin_groups=admin_groups,
                                   ssh_key_pwd=ssh_key_pwd,
                                   is_active=is_active,
                                   date_joined=datetime.datetime.now())
                server_add_user(username, password, ssh_key_pwd, ssh_key_login_need)
            except Exception, e:
                error = u'添加用户 %s 失败 %s ' % (username, e)
                try:
                    db_del_user(username)
                    server_del_user(username)
                except Exception:
                    pass
            else:
                if MAIL_ENABLE and send_mail_need:
                    user_add_mail(user, kwargs=locals())
                msg = get_display_msg(user, password, ssh_key_pwd, ssh_key_login_need, send_mail_need)
    return my_render('juser/user_add.html', locals(), request)


# @require_role(role='admin')
# def user_add_adm(request):
#     error = ''
#     msg = ''
#     header_title, path1, path2 = '添加用户', '用户管理', '添加用户'
#     user, dept = get_session_user_dept(request)
#     group_all = dept.usergroup_set.all()
#
#     if request.method == 'POST':
#         username = request.POST.get('username', '')
#         password = PyCrypt.gen_rand_pwd(16)
#         name = request.POST.get('name', '')
#         email = request.POST.get('email', '')
#         groups = request.POST.getlist('groups', [])
#         ssh_key_pwd = PyCrypt.gen_rand_pwd(16)
#         is_active = True if request.POST.get('is_active', '1') == '1' else False
#         ldap_pwd = PyCrypt.gen_rand_pwd(16)
#
#         try:
#             if '' in [username, password, ssh_key_pwd, name, groups, is_active]:
#                 error = u'带*内容不能为空'
#                 raise ServerError
#             user = User.objects.filter(username=username)
#             if user:
#                 error = u'用户 %s 已存在' % username
#                 raise ServerError
#
#         except ServerError:
#             pass
#         else:
#             try:
#                 user = db_add_user(username=username,
#                                    password=CRYPTOR.md5_crypt(password),
#                                    name=name, email=email, dept=dept,
#                                    groups=groups, role='CU',
#                                    ssh_key_pwd=CRYPTOR.md5_crypt(ssh_key_pwd),
#                                    ldap_pwd=CRYPTOR.encrypt(ldap_pwd),
#                                    is_active=is_active,
#                                    date_joined=datetime.datetime.now())
#
#                 server_add_user(username, password, ssh_key_pwd)
#                 if LDAP_ENABLE:
#                     ldap_add_user(username, ldap_pwd)
#
#             except Exception, e:
#                 error = u'添加用户 %s 失败 %s ' % (username, e)
#                 try:
#                     db_del_user(username)
#                     server_del_user(username)
#                     if LDAP_ENABLE:
#                         ldap_del_user(username)
#                 except Exception:
#                     pass
#             else:
#                 mail_title = u'恭喜你的跳板机用户添加成功 Jumpserver'
#                 mail_msg = """
#                 Hi, %s
#                     您的用户名： %s
#                     您的部门: %s
#                     您的角色： %s
#                     您的web登录密码： %s
#                     您的ssh密钥文件密码： %s
#                     密钥下载地址： http://%s:%s/juser/down_key/?id=%s
#                     说明： 请登陆后再下载密钥！
#                 """ % (name, username, dept.name, '普通用户',
#                        password, ssh_key_pwd, SEND_IP, SEND_PORT, user.id)
#                 send_mail(mail_title, mail_msg, MAIL_FROM, [email], fail_silently=False)
#                 msg = u'添加用户 %s 成功！ 用户密码已发送到 %s 邮箱！' % (username, email)
#
#     return render_to_response('juser/user_add.html', locals(), context_instance=RequestContext(request))


@require_role(role='super')
def user_list(request):
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    header_title, path1, path2 = '查看用户', '用户管理', '用户列表'
    keyword = request.GET.get('keyword', '')
    gid = request.GET.get('gid', '')
    users_list = User.objects.all().order_by('username')

    if gid:
        user_group = UserGroup.objects.filter(id=gid)
        if user_group:
            user_group = user_group[0]
            users_list = user_group.user_set.all()

    if keyword:
        users_list = users_list.filter(Q(username__icontains=keyword) | Q(name__icontains=keyword)).order_by('username')

    users_list, p, users, page_range, current_page, show_first, show_end = pages(users_list, request)

    return my_render('juser/user_list.html', locals(), request)


# @require_role(role='admin')
# def user_list_adm(request):
#     user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
#     header_title, path1, path2 = '查看用户', '用户管理', '用户列表'
#     keyword = request.GET.get('keyword', '')
#     user, dept = get_session_user_dept(request)
#     gid = request.GET.get('gid', '')
#     contact_list = dept.user_set.all().order_by('name')
#
#     if gid:
#         if not validate(request, user_group=[gid]):
#             return HttpResponseRedirect('/juser/user_list/')
#         user_group = UserGroup.objects.filter(id=gid)
#         if user_group:
#             user_group = user_group[0]
#             contact_list = user_group.user_set.all()
#
#     if keyword:
#         contact_list = contact_list.filter(Q(username__icontains=keyword) | Q(name__icontains=keyword)).order_by('name')
#
#     contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)
#
#     return render_to_response('juser/user_list.html', locals(), context_instance=RequestContext(request))


@require_role(role='user')
def user_detail(request):
    header_title, path1, path2 = '用户详情', '用户管理', '用户详情'
    # if request.session.get('role_id') == 0:
    #     user_id = request.user.id
    # else:
    #     user_id = request.GET.get('id', '')
    #     if request.session.get('role_id') == 1:
    #         user, dept = get_session_user_dept(request)
    #         if not validate(request, user=[user_id]):
    #             return HttpResponseRedirect('/')
    # if not user_id:
    #     return HttpResponseRedirect('/juser/user_list/')

    # user = get_object(User, id=user_id)
    # if user:
    #     pass
        # asset_group_permed = user.get_asset_group()
        # logs_last = Log.objects.filter(user=user.name).order_by('-start_time')[0:10]
        # logs_all = Log.objects.filter(user=user.name).order_by('-start_time')
        # logs_num = len(logs_all)

    return my_render('juser/user_detail.html', locals(), request)


@require_role(role='admin')
def user_del(request):
    if request.method == "GET":
        user_ids = request.GET.get('id', '')
        user_id_list = user_ids.split(',')
    elif request.method == "POST":
        user_ids = request.POST.get('id', '')
        user_id_list = user_ids.split(',')
    else:
        return HttpResponse('错误请求')
    for user_id in user_id_list:
        User.objects.filter(id=user_id).delete()

    return HttpResponse('删除成功')


@require_role('admin')
def send_mail_retry(request):
    user_uuid = request.GET.get('uuid', '1')
    user = get_object(User, uuid=user_uuid)
    msg = u"""
    跳板机地址： %s
    用户名：%s
    重设密码：%s/juser/forget_password/
    请登录web重新生成key
    """ % (URL, user.username, URL)

    try:
        send_mail(u'邮件重发', msg, MAIL_FROM, [user.email], fail_silently=False)
    except IndexError:
        return Http404
    return HttpResponse('发送成功')


def forget_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '')
        username = request.POST.get('username', '')
        user = get_object(User, username=username, email=email)
        if user:
            timestamp = int(time.time())
            hash_encode = PyCrypt.md5_crypt(str(user.uuid) + str(timestamp) + KEY)
            msg = u"""
            Hi %s, 请点击下面链接重设密码！
            %s/juser/reset_password/?uuid=%s&timestamp=%s&hash=%s
            """ % (user.name, URL, user.uuid, timestamp, hash_encode)
            send_mail('忘记跳板机密码', msg, MAIL_FROM, [email], fail_silently=False)
            msg = u'请登陆邮箱，点击邮件重设密码'
            return HttpResponse(msg)
        else:
            error = u'用户不存在或邮件地址错误'

    return render_to_response('juser/forget_password.html', locals())


def reset_password(request):
    uuid = request.GET.get('uuid', '')
    timestamp = request.GET.get('timestamp', '')
    hash_encode = request.GET.get('hash', '')
    action = '/juser/reset_password/?uuid=%s&timestamp=%s&hash=%s' % (uuid, timestamp, hash_encode)

    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        if password != password_confirm:
            return HttpResponse('密码不匹配')
        else:
            user = get_object(User, uuid=uuid)
            if user:
                user.password = PyCrypt.md5_crypt(password)
                user.save()
                return HttpResponse('密码重设成功')
            else:
                return HttpResponse('用户不存在')

    if hash_encode == PyCrypt.md5_crypt(uuid + timestamp + KEY):
        if int(time.time()) - int(timestamp) > 600:
            return HttpResponse('链接已超时')
        else:
            return render_to_response('juser/reset_password.html', locals())

    return http_error(request, u'错误请求')


@require_role(role='super')
def user_edit(request):
    header_title, path1, path2 = '编辑用户', '用户管理', '编辑用户'
    if request.method == 'GET':
        user_id = request.GET.get('id', '')
        if not user_id:
            return HttpResponseRedirect('/')

        user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
        user = get_object(User, id=user_id)
        group_all = UserGroup.objects.all()
        if user:
            groups_str = ' '.join([str(group.id) for group in user.group.all()])
            admin_groups_str = ' '.join([str(admin_group.group.id) for admin_group in user.admingroup_set.all()])

    else:
        user_id = request.GET.get('id', '')
        password = request.POST.get('password', '')
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        groups = request.POST.getlist('groups', [])
        role_post = request.POST.get('role', 'CU')
        admin_groups = request.POST.getlist('admin_groups', [])
        extra = request.POST.getlist('extra', [])
        is_active = True if '0' in extra else False
        email_need = True if '2' in extra else False
        user_role = {'SU': u'超级管理员', 'GA': u'部门管理员', 'CU': u'普通用户'}

        if user_id:
            user = get_object(User, id=user_id)
        else:
            return HttpResponseRedirect('/juser/user_list/')

        # if password != user.password:
        #     password_decode = password
        #     password = CRYPTOR.md5_crypt(password)
        # else:
        #     password_decode = None

        db_update_user(user_id=user_id,
                       password=password,
                       name=name,
                       email=email,
                       groups=groups,
                       admin_groups=admin_groups,
                       role=role_post,
                       is_active=is_active)

        if email_need:
            msg = u"""
            Hi %s:
                您的信息已修改，请登录跳板机查看详细信息
                地址：%s
                用户名： %s
                密码：%s (如果密码为None代表密码为原密码)
                角色：%s

            """ % (user.name, URL, user.username, password_decode, user_role.get(role_post, u''))
            send_mail('您的信息已修改', msg, MAIL_FROM, [email], fail_silently=False)

        return HttpResponseRedirect('/juser/user_list/')

    return my_render('juser/user_edit.html', locals(), request)


# @require_role(role='admin')
def user_edit_adm(request):
    pass
#     header_title, path1, path2 = '编辑用户', '用户管理', '用户编辑'
#     user, dept = get_session_user_dept(request)
#     if request.method == 'GET':
#         user_id = request.GET.get('id', '')
#         if not user_id:
#             return HttpResponseRedirect('/juser/user_list/')
#
#         if not validate(request, user=[user_id]):
#             return HttpResponseRedirect('/juser/user_list/')
#
#         user = User.objects.filter(id=user_id)
#         dept_all = DEPT.objects.all()
#         group_all = dept.usergroup_set.all()
#         if user:
#             user = user[0]
#             groups_str = ' '.join([str(group.id) for group in user.group.all()])
#
#     else:
#         user_id = request.POST.get('user_id', '')
#         password = request.POST.get('password', '')
#         name = request.POST.get('name', '')
#         email = request.POST.get('email', '')
#         groups = request.POST.getlist('groups', [])
#         ssh_key_pwd = request.POST.get('ssh_key_pwd', '')
#         is_active = True if request.POST.get('is_active', '1') == '1' else False
#
#         if not validate(request, user=[user_id], user_group=groups):
#             return HttpResponseRedirect('/juser/user_edit/')
#         if user_id:
#             user = User.objects.filter(id=user_id)
#             if user:
#                 user = user[0]
#         else:
#             return HttpResponseRedirect('/juser/user_list/')
#
#         if password != user.password:
#             password = CRYPTOR.md5_crypt(password)
#
#         if ssh_key_pwd != user.ssh_key_pwd:
#             ssh_key_pwd = CRYPTOR.encrypt(ssh_key_pwd)
#
#         db_update_user(user_id=user_id,
#                        password=password,
#                        name=name,
#                        email=email,
#                        groups=groups,
#                        is_active=is_active,
#                        ssh_key_pwd=ssh_key_pwd)
#
#         return HttpResponseRedirect('/juser/user_list/')
#
#     return render_to_response('juser/user_edit.html', locals(), context_instance=RequestContext(request))
#


def profile(request):
    a = request.user.id
    a = request.user.groups

    user_id = request.user.id
    if not user_id:
        return HttpResponseRedirect('/')
    user = User.objects.get(id=user_id)
    return render_to_response('juser/profile.html', locals(), context_instance=RequestContext(request))


def change_info(request):
    header_title, path1, path2 = '修改信息', '用户管理', '修改个人信息'
    user_id = request.user.id
    user = get_object(User, id=user_id)
    error = ''
    if not user:
        return HttpResponseRedirect('/')

    if request.method == 'POST':
        name = request.POST.get('name', '')
        password = request.POST.get('password', '')
        email = request.POST.get('email', '')

        if '' in [name, password, email]:
            error = '不能为空'

        if len(password) < 6:
            error = '密码须大于6位'

        if not error:
            # if password != user.password:
            #     password = CRYPTOR.md5_crypt(password)

            user.update(name=name, email=email)
            user.set_password(password)
            msg = '修改成功'

    return render_to_response('juser/change_info.html', locals(), context_instance=RequestContext(request))


@require_role(role='user')
def regen_ssh_key(request):
    uuid = request.GET.get('uuid', '')
    user = get_object(User, uuid=uuid)
    if not user:
        return HttpResponse('没有该用户')

    username = user.username
    ssh_key_pass = PyCrypt.random_pass(16)
    gen_ssh_key(username, ssh_key_pass)
    return HttpResponse('ssh密钥已生成，密码为 %s, 请到下载页面下载' % ssh_key_pass)


@require_role(role='user')
def down_key(request):
    user_id = ''
    if is_role_request(request, 'super'):
        user_id = request.GET.get('id')

    if is_role_request(request, 'user'):
        user_id = request.user.id

    if user_id:
        user = get_object(User, id=user_id)
        if user:
            username = user.username
            private_key_file = os.path.join(BASE_DIR, 'keys/jumpserver', username+".pem")
            if os.path.isfile(private_key_file):
                f = open(private_key_file)
                data = f.read()
                f.close()
                response = HttpResponse(data, content_type='application/octet-stream')
                response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(private_key_file)
                return response

    return HttpResponse('No Key File. Contact Admin.')