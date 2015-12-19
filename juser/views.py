# coding: utf-8
# Author: Guanghongwei
# Email: ibuler@qq.com

# import random
# from Crypto.PublicKey import RSA
import uuid
from django.contrib.auth.decorators import login_required

from django.db.models import Q
from juser.user_api import *
from jperm.perm_api import get_group_user_perm

MAIL_FROM = EMAIL_HOST_USER


<<<<<<< HEAD
def gen_rand_pwd(num):
    """生成随机密码"""
    seed = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    salt_list = []
    for i in range(num):
        salt_list.append(random.choice(seed))
    salt = ''.join(salt_list)
    return salt


class AddError(Exception):
    pass


def gen_sha512(salt, password):
    return crypt.crypt(password, '$6$%s$' % salt)


def group_add_user(group, user_id=None, username=None):
    try:
        if user_id:
            user = User.objects.get(id=user_id)
        else:
            user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        raise AddError('用户获取失败')
    else:
        group.user_set.add(user)


def db_add_group(**kwargs):
    name = kwargs.get('name')
    group = UserGroup.objects.filter(name=name)
    users = kwargs.pop('users')
    if group:
        raise AddError(u'用户组 %s 已经存在' % name)
    group = UserGroup(**kwargs)
    group.save()
    for user_id in users:
        group_add_user(group, user_id)


def db_add_user(**kwargs):
    groups_post = kwargs.pop('groups')
    user = User(**kwargs)
    user.save()
    if groups_post:
        group_select = []
        for group_id in groups_post:
            group = UserGroup.objects.filter(id=group_id)
            group_select.extend(group)
        user.group = group_select
    return user


def db_update_user(**kwargs):
    groups_post = kwargs.pop('groups')
    user_id = kwargs.pop('user_id')
    user = User.objects.filter(id=user_id)
    if user:
        user.update(**kwargs)
        user = User.objects.get(id=user_id)
        user.save()

    if groups_post:
        group_select = []
        for group_id in groups_post:
            group = UserGroup.objects.filter(id=group_id)
            group_select.extend(group)
        user.group = group_select


def db_del_user(username):
    try:
        user = User.objects.get(username=username)
        user.delete()
    except ObjectDoesNotExist:
        pass


def gen_ssh_key(username, password=None, length=2048):
    private_key_dir = os.path.join(BASE_DIR, 'keys/jumpserver/')
    private_key_file = os.path.join(private_key_dir, username+".pem")
    public_key_dir = '/home/%s/.ssh/' % username
    public_key_file = os.path.join(public_key_dir, 'authorized_keys')
    is_dir(private_key_dir)
    is_dir(public_key_dir, username, mode=0700)

    key = RSA.generate(length)
    with open(private_key_file, 'w') as pri_f:
        pri_f.write(key.exportKey('PEM', password))
    os.chmod(private_key_file, 0600)

    pub_key = key.publickey()
    with open(public_key_file, 'w') as pub_f:
        pub_f.write(pub_key.exportKey('OpenSSH'))
    os.chmod(public_key_file, 0600)
    bash('chown %s:%s %s' % (username, username, public_key_file))


def server_add_user(username, password, ssh_key_pwd):
    bash("useradd '%s'; echo '%s' | passwd --stdin '%s'" % (username, password, username))
    gen_ssh_key(username, ssh_key_pwd)


def server_del_user(username):
    bash('userdel -r %s' % username)


def ldap_add_user(username, ldap_pwd):
    if LDAP_ENABLE:
        ldap_conn = LDAPMgmt(LDAP_HOST_URL, LDAP_BASE_DN, LDAP_ROOT_DN, LDAP_ROOT_PW)
    else:
        return
    user_dn = "uid=%s,ou=People,%s" % (username, LDAP_BASE_DN)
    password_sha512 = gen_sha512(gen_rand_pwd(6), ldap_pwd)
    user = User.objects.filter(username=username)
    if user:
        user = user[0]
    else:
        raise AddError(u'用户 %s 不存在' % username)

    user_attr = {'uid': [str(username)],
                 'cn': [str(username)],
                 'objectClass': ['account', 'posixAccount', 'top', 'shadowAccount'],
                 'userPassword': ['{crypt}%s' % password_sha512],
                 'shadowLastChange': ['16328'],
                 'shadowMin': ['0'],
                 'shadowMax': ['99999'],
                 'shadowWarning': ['7'],
                 'loginShell': ['/bin/bash'],
                 'uidNumber': [str(user.id)],
                 'gidNumber': [str(user.id)],
                 'homeDirectory': [str('/home/%s' % username)]}

    group_dn = "cn=%s,ou=Group,%s" % (username, LDAP_BASE_DN)
    group_attr = {'objectClass': ['posixGroup', 'top'],
                  'cn': [str(username)],
                  'userPassword': ['{crypt}x'],
                  'gidNumber': [str(user.id)]}

    ldap_conn.add(user_dn, user_attr)
    ldap_conn.add(group_dn, group_attr)


def ldap_del_user(username):
    if LDAP_ENABLE:
        ldap_conn = LDAPMgmt(LDAP_HOST_URL, LDAP_BASE_DN, LDAP_ROOT_DN, LDAP_ROOT_PW)
    else:
        return
    user_dn = "uid=%s,ou=People,%s" % (username, LDAP_BASE_DN)
    group_dn = "cn=%s,ou=Group,%s" % (username, LDAP_BASE_DN)
    sudo_dn = 'cn=%s,ou=Sudoers,%s' % (username, LDAP_BASE_DN)

    ldap_conn.delete(user_dn)
    ldap_conn.delete(group_dn)
    ldap_conn.delete(sudo_dn)


@require_super_user
def dept_add(request):
    header_title, path1, path2 = '添加部门', '用户管理', '添加部门'
    if request.method == 'POST':
        name = request.POST.get('name', '')
        comment = request.POST.get('comment', '')

        try:
            if not name:
                raise AddError('部门名称不能为空')
            if DEPT.objects.filter(name=name):
                raise AddError(u'部门名称 %s 已存在' % name)
        except AddError, e:
            error = e
        else:
            DEPT(name=name, comment=comment).save()
            msg = u'添加部门 %s 成功' % name

    return render_to_response('juser/dept_add.html', locals(), context_instance=RequestContext(request))


@require_super_user
def dept_list(request):
    header_title, path1, path2 = '查看部门', '用户管理', '查看部门'
    keyword = request.GET.get('search')
    if keyword:
        contact_list = DEPT.objects.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword)).order_by('name')
    else:
        contact_list = DEPT.objects.all().order_by('id')

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)

    return render_to_response('juser/dept_list.html', locals(), context_instance=RequestContext(request))


@require_admin
def dept_list_adm(request):
    header_title, path1, path2 = '查看部门', '用户管理', '查看部门'
    user, dept = get_session_user_dept(request)
    contact_list = [dept]
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)

    return render_to_response('juser/dept_list.html', locals(), context_instance=RequestContext(request))


def chg_role(request):
    role = {'SU': 2, 'DA': 1, 'CU': 0}
    user, dept = get_session_user_dept(request)
    if request.session['role_id'] > 0:
        request.session['role_id'] = 0
    elif request.session['role_id'] == 0:
        request.session['role_id'] = role.get(user.role, 0)
    return HttpResponseRedirect('/')


@require_super_user
def dept_detail(request):
    dept_id = request.GET.get('id', None)
    if not dept_id:
        return HttpResponseRedirect('/juser/dept_list/')
    dept = DEPT.objects.filter(id=dept_id)
    if dept:
        dept = dept[0]
        users = dept.user_set.all()
    return render_to_response('juser/dept_detail.html', locals(), context_instance=RequestContext(request))


@require_super_user
def dept_del(request):
    dept_id = request.GET.get('id', None)
    if not dept_id or dept_id in ['1', '2']:
        return HttpResponseRedirect('/juser/dept_list/')
    dept = DEPT.objects.filter(id=dept_id)
    if dept:
        dept = dept[0]
        dept.delete()
    return HttpResponseRedirect('/juser/dept_list/')


def dept_member(dept_id):
    dept = DEPT.objects.filter(id=dept_id)
    if dept:
        dept = dept[0]
        return dept.user_set.all()


def dept_member_update(dept, users_id_list):
    old_users = dept.user_set.all()
    new_users = []
    for user_id in users_id_list:
        new_users.extend(User.objects.filter(id=user_id))

    remove_user = [user for user in old_users if user not in new_users]
    add_user = [user for user in new_users if user not in old_users]

    for user in add_user:
        user.dept = dept
        user.save()

    dept_default = DEPT.objects.get(id=2)
    for user in remove_user:
        user.dept = dept_default
        user.save()


@require_super_user
def dept_del_ajax(request):
    dept_ids = request.POST.get('dept_ids')
    for dept_id in dept_ids.split(','):
        if int(dept_id) > 2:
            DEPT.objects.filter(id=dept_id).delete()
    return HttpResponse("删除成功")


@require_super_user
def dept_edit(request):
    header_title, path1, path2 = '部门编辑', '用户管理', '部门编辑'
    if request.method == 'GET':
        dept_id = request.GET.get('id', '')
        if dept_id:
            dept = DEPT.objects.filter(id=dept_id)
            if dept:
                dept = dept[0]
                users = dept_member(dept_id)
                users_all = User.objects.all()
                users_other = [user for user in users_all if user not in users]
            else:
                error = 'id 错误'
        else:
            error = u'部门不存在'
    else:
        dept_id = request.POST.get('id', '')
        name = request.POST.get('name', '')
        users = request.POST.getlist('users_selected', [])
        comment = request.POST.get('comment', '')

        dept = DEPT.objects.filter(id=dept_id)
        if dept:
            dept.update(name=name, comment=comment)
            dept_member_update(dept[0], users)
        else:
            error = '部门不存在'
        return HttpResponseRedirect('/juser/dept_list/')
    return render_to_response('juser/dept_edit.html', locals(), context_instance=RequestContext(request))


def dept_user_ajax(request):
    dept_id = request.GET.get('id', '4')
    if dept_id not in ['1', '2']:
        dept = DEPT.objects.filter(id=dept_id)
        if dept:
            dept = dept[0]
            users = dept.user_set.all()
    else:
        users = User.objects.all()

    return render_to_response('juser/dept_user_ajax.html', locals())



@require_super_user
=======
@require_role(role='super')
>>>>>>> dev
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
            for user in User.objects.filter(id__in=users_selected):
                user.group.add(UserGroup.objects.get(id=group_id))
            # delete user group
            user_group = UserGroup.objects.get(id=group_id)
            for user in [user for user in User.objects.filter(group=user_group) if user not in User.objects.filter(id__in=users_selected)]:
                user_group_all = user.group.all()
                user.group.clear()
                for g in user_group_all:
                    if g == user_group:
                        continue
                    user.group.add(g)
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
        ssh_key_login_need = True
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
                                   email=email, role=role, uuid=uuid_r,
                                   groups=groups, admin_groups=admin_groups,
                                   ssh_key_pwd=ssh_key_pwd,
                                   is_active=is_active,
                                   date_joined=datetime.datetime.now())
                server_add_user(username, password, ssh_key_pwd, ssh_key_login_need)
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
                msg = get_display_msg(user, password, ssh_key_pwd, ssh_key_login_need, send_mail_need)
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
            bash('userdel -r %s' % user.username)
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

    if request.method == 'POST':
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        print password, password_confirm
        if password != password_confirm:
            return HttpResponse('密码不匹配')
        else:
            user = get_object(User, uuid=uuid_r)
            if user:
                user.password = PyCrypt.md5_crypt(password)
                user.save()
                return http_success(request, u'密码重设成功')
            else:
                return HttpResponse('用户不存在')

    if hash_encode == PyCrypt.md5_crypt(uuid_r + timestamp + KEY):
        if int(time.time()) - int(timestamp) > 600:
            return http_error(request, u'链接已超时')
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
        email_need = True if '2' in extra else False
        user_role = {'SU': u'超级管理员', 'GA': u'部门管理员', 'CU': u'普通用户'}

        if user_id:
            user = get_object(User, id=user_id)
        else:
            return HttpResponseRedirect(reverse('user_list'))

        if password != '':
            password_decode = password
        else:
            password_decode = None

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

            """ % (user.name, URL, user.username, password_decode, user_role.get(role_post, u''))
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
            User.objects.filter(id=user_id).update(name=name, email=email)
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
                return response
    return HttpResponse('No Key File. Contact Admin.')

