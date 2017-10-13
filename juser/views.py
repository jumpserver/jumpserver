# coding: utf-8
# Author: Guanghongwei
# Email: ibuler@qq.com

# import random
# from Crypto.PublicKey import RSA
import uuid
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db.models import Q
from juser.user_api import *
from jperm.perm_api import get_group_user_perm
import re

MAIL_FROM = EMAIL_HOST_USER


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
    group_id = request.GET.get('id', '')

    if keyword:
        user_group_list = user_group_list.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))

    if group_id:
        user_group_list = user_group_list.filter(id=int(group_id))

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


@require_role(role='super')
def group_edit(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '编辑用户组', '用户管理', '编辑用户组'

    if request.method == 'GET':
        group_id = request.GET.get('id', '')
        user_group = get_object(UserGroup, id=group_id)
        # user_group = UserGroup.objects.get(id=group_id)
        users_selected = User.objects.filter(group=user_group)
        users_remain = User.objects.filter(~Q(group=user_group))
        users_all = User.objects.all()

    elif request.method == 'POST':
        group_id = request.POST.get('group_id', '')
        group_name = request.POST.get('group_name', '')
        comment = request.POST.get('comment', '')
        users_selected = request.POST.getlist('users_selected')

        try:
            if '' in [group_id, group_name]:
                raise ServerError('组名不能为空')

            if len(UserGroup.objects.filter(name=group_name)) > 1:
                raise ServerError(u'%s 用户组已存在' % group_name)
            # add user group
            user_group = get_object_or_404(UserGroup, id=group_id)
            user_group.user_set.clear()

            for user in User.objects.filter(id__in=users_selected):
                user.group.add(UserGroup.objects.get(id=group_id))

            user_group.name = group_name
            user_group.comment = comment
            user_group.save()
        except ServerError, e:
            error = e

        if not error:
            return HttpResponseRedirect(reverse('user_group_list'))
        else:
            users_all = User.objects.all()
            users_selected = User.objects.filter(group=user_group)
            users_remain = User.objects.filter(~Q(group=user_group))

    return my_render('juser/group_edit.html', locals(), request)


@require_role(role='super')
def user_add(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '添加用户', '用户管理', '添加用户'
    user_role = {'SU': u'超级管理员', 'CU': u'普通用户'}
    group_all = UserGroup.objects.all()

    if request.method == 'POST':
        username = request.POST.get('username', '')      
        password = PyCrypt.gen_rand_pass(16)
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        groups = request.POST.getlist('groups', [])
        admin_groups = request.POST.getlist('admin_groups', [])
        role = request.POST.get('role', 'CU')
        uuid_r = uuid.uuid4().get_hex()
        ssh_key_pwd = PyCrypt.gen_rand_pass(16)
        extra = request.POST.getlist('extra', [])
        is_active = False if '0' in extra else True
        send_mail_need = True if '1' in extra else False

        try:
            if '' in [username, password, ssh_key_pwd, name, role]:
                error = u'带*内容不能为空'
                raise ServerError
                
            check_user_is_exist = User.objects.filter(username=username)
            if check_user_is_exist:
                error = u'用户 %s 已存在' % username
                raise ServerError
            
            if username in ['root']:
                error = u'用户不能为root'
                raise ServerError

        except ServerError:
            pass
        else:
            try:
                if not re.match(r"^\w+$",username):
                    error = u'用户名不合法'
                    raise ServerError(error)
                user = db_add_user(username=username, name=name,
                                   password=password,
                                   email=email, role=role, uuid=uuid_r,
                                   groups=groups, admin_groups=admin_groups,
                                   ssh_key_pwd=ssh_key_pwd,
                                   is_active=is_active,
                                   date_joined=datetime.datetime.now())
                server_add_user(username=username, ssh_key_pwd=ssh_key_pwd)
                user = get_object(User, username=username)
                if groups:
                    user_groups = []
                    for user_group_id in groups:
                        user_groups.extend(UserGroup.objects.filter(id=user_group_id))

            except IndexError, e:
                error = u'添加用户 %s 失败 %s ' % (username, e)
                try:
                    db_del_user(username)
                    server_del_user(username)
                except Exception:
                    pass
            else:
                if MAIL_ENABLE and send_mail_need:
                    user_add_mail(user, kwargs=locals())
                msg = get_display_msg(user, password=password, ssh_key_pwd=ssh_key_pwd, send_mail_need=send_mail_need)
    return my_render('juser/user_add.html', locals(), request)


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


@require_role(role='user')
def user_detail(request):
    header_title, path1, path2 = '用户详情', '用户管理', '用户详情'
    if request.session.get('role_id') == 0:
        user_id = request.user.id
    else:
        user_id = request.GET.get('id', '')

    user = get_object(User, id=user_id)
    if not user:
        return HttpResponseRedirect(reverse('user_list'))

    user_perm_info = get_group_user_perm(user)
    role_assets = user_perm_info.get('role')
    user_log_ten = Log.objects.filter(user=user.username).order_by('id')[0:10]
    user_log_last = Log.objects.filter(user=user.username).order_by('id')[0:50]
    user_log_last_num = len(user_log_last)

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
        user = get_object(User, id=user_id)
        if user and user.username != 'admin':
            logger.debug(u"删除用户 %s " % user.username)
            server_del_user(user.username)
            user.delete()
    return HttpResponse('删除成功')


@require_role('admin')
def send_mail_retry(request):
    uuid_r = request.GET.get('uuid', '1')
    user = get_object(User, uuid=uuid_r)
    msg = u"""
    跳板机地址： %s
    用户名：%s
    重设密码：%s/juser/password/forget/
    请登录web点击个人信息页面重新生成ssh密钥
    """ % (URL, user.username, URL)

    try:
        send_mail(u'邮件重发', msg, MAIL_FROM, [user.email], fail_silently=False)
    except IndexError:
        return Http404
    return HttpResponse('发送成功')


@defend_attack
def forget_password(request):
    if request.method == 'POST':
        defend_attack(request)
        email = request.POST.get('email', '')
        username = request.POST.get('username', '')
        name = request.POST.get('name', '')
        user = get_object(User, username=username, email=email, name=name)
        if user:
            timestamp = int(time.time())
            hash_encode = PyCrypt.md5_crypt(str(user.uuid) + str(timestamp) + KEY)
            msg = u"""
            Hi %s, 请点击下面链接重设密码！
            %s/juser/password/reset/?uuid=%s&timestamp=%s&hash=%s
            """ % (user.name, URL, user.uuid, timestamp, hash_encode)
            send_mail('忘记跳板机密码', msg, MAIL_FROM, [email], fail_silently=False)
            msg = u'请登陆邮箱，点击邮件重设密码'
            return http_success(request, msg)
        else:
            error = u'用户不存在或邮件地址错误'

    return render_to_response('juser/forget_password.html', locals())


@defend_attack
def reset_password(request):
    uuid_r = request.GET.get('uuid', '')
    timestamp = request.GET.get('timestamp', '')
    hash_encode = request.GET.get('hash', '')
    action = '/juser/password/reset/?uuid=%s&timestamp=%s&hash=%s' % (uuid_r, timestamp, hash_encode)

    if hash_encode == PyCrypt.md5_crypt(uuid_r + timestamp + KEY):
        if int(time.time()) - int(timestamp) > 600:
            return http_error(request, u'链接已超时')
    else:
        return HttpResponse('hash校验失败')

    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        print password, password_confirm
        if password != password_confirm:
            return HttpResponse('密码不匹配')
        else:
            user = get_object(User, uuid=uuid_r)
            if user:
                user.set_password(password)
                user.save()
                return http_success(request, u'密码重设成功')
            else:
                return HttpResponse('用户不存在')

    else:
        return render_to_response('juser/reset_password.html', locals())

    return http_error(request, u'错误请求')


@require_role(role='super')
def user_edit(request):
    header_title, path1, path2 = '编辑用户', '用户管理', '编辑用户'
    if request.method == 'GET':
        user_id = request.GET.get('id', '')
        if not user_id:
            return HttpResponseRedirect(reverse('index'))

        user_role = {'SU': u'超级管理员', 'CU': u'普通用户'}
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
        email_need = True if '1' in extra else False
        user_role = {'SU': u'超级管理员', 'GA': u'部门管理员', 'CU': u'普通用户'}

        if user_id:
            user = get_object(User, id=user_id)
        else:
            return HttpResponseRedirect(reverse('user_list'))

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
                权限：：%s

            """ % (user.name, URL, user.username, password, user_role.get(role_post, u''))
            send_mail('您的信息已修改', msg, MAIL_FROM, [email], fail_silently=False)

        return HttpResponseRedirect(reverse('user_list'))
    return my_render('juser/user_edit.html', locals(), request)


@require_role('user')
def profile(request):
    user_id = request.user.id
    if not user_id:
        return HttpResponseRedirect(reverse('index'))
    user = User.objects.get(id=user_id)
    return my_render('juser/profile.html', locals(), request)


def change_info(request):
    header_title, path1, path2 = '修改信息', '用户管理', '修改个人信息'
    user_id = request.user.id
    user = User.objects.get(id=user_id)
    error = ''
    if not user:
        return HttpResponseRedirect(reverse('index'))

    if request.method == 'POST':
        name = request.POST.get('name', '')
        password = request.POST.get('password', '')
        email = request.POST.get('email', '')

        if '' in [name, email]:
            error = '不能为空'

        if not error:
            user.name = name
            user.email = email
            user.save()
            if len(password) > 0:
                user.set_password(password)
                user.save()
            msg = '修改成功'

    return my_render('juser/change_info.html', locals(), request)


@require_role(role='user')
def regen_ssh_key(request):
    uuid_r = request.GET.get('uuid', '')
    user = get_object(User, uuid=uuid_r)
    if not user:
        return HttpResponse('没有该用户')

    username = user.username
    ssh_key_pass = PyCrypt.gen_rand_pass(16)
    gen_ssh_key(username, ssh_key_pass)
    return HttpResponse('ssh密钥已生成，密码为 %s, 请到下载页面下载' % ssh_key_pass)


@require_role(role='user')
def down_key(request):
    if is_role_request(request, 'super'):
        uuid_r = request.GET.get('uuid', '')
    else:
        uuid_r = request.user.uuid
    if uuid_r:
        user = get_object(User, uuid=uuid_r)
        if user:
            username = user.username
            private_key_file = os.path.join(KEY_DIR, 'user', username+'.pem')
            print private_key_file
            if os.path.isfile(private_key_file):
                f = open(private_key_file)
                data = f.read()
                f.close()
                response = HttpResponse(data, content_type='application/octet-stream')
                response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(private_key_file)
                if request.user.role == 'CU':
                    os.unlink(private_key_file)
                return response
    return HttpResponse('No Key File. Contact Admin.')

