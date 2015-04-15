# coding: utf-8
# Author: Guanghongwei
# Email: ibuler@qq.com

import random
import subprocess
from Crypto.PublicKey import RSA
import crypt

from django.shortcuts import render_to_response
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template import RequestContext

from juser.models import DEPT
from jumpserver.api import *


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


def db_update_user(**kwargs):
    print kwargs
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

    # sudo_dn = 'cn=%s,ou=Sudoers,%s' % (username, LDAP_BASE_DN)
    # sudo_attr = {'objectClass': ['top', 'sudoRole'],
    #              'cn': ['%s' % str(username)],
    #              'sudoCommand': ['/bin/pwd'],
    #              'sudoHost': ['192.168.1.1'],
    #              'sudoOption': ['!authenticate'],
    #              'sudoRunAsUser': ['root'],
    #              'sudoUser': ['%s' % str(username)]}

    ldap_conn.add(user_dn, user_attr)
    ldap_conn.add(group_dn, group_attr)
    # ldap_conn.add(sudo_dn, sudo_attr)


def ldap_del_user(username):
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
def group_add(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '添加小组', '用户管理', '添加小组'
    user_all = User.objects.all()
    dept_all = DEPT.objects.all()

    if request.method == 'POST':
        group_name = request.POST.get('group_name', '')
        dept_id = request.POST.get('dept_id', '')
        users_selected = request.POST.getlist('users_selected', '')
        comment = request.POST.get('comment', '')

        try:
            if '' in [group_name, dept_id]:
                error = u'组名 或 部门 不能为空'
                raise AddError(error)

            if UserGroup.objects.filter(name=group_name):
                error = u'组名已存在'
                raise AddError(error)

            dept = DEPT.objects.filter(id=dept_id)
            if dept:
                dept = dept[0]
            else:
                error = u'部门不存在'
                raise AddError(error)

            db_add_group(name=group_name, users=users_selected, dept=dept, comment=comment)
        except AddError:
            pass
        except TypeError:
            error = u'保存小组失败'
        else:
            msg = u'添加组 %s 成功' % group_name

    return render_to_response('juser/group_add.html', locals(), context_instance=RequestContext(request))


@require_admin
def group_add_adm(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '添加小组', '用户管理', '添加小组'
    user, dept = get_session_user_dept(request)
    user_all = dept.user_set.all()

    if request.method == 'POST':
        group_name = request.POST.get('group_name', '')
        users_selected = request.POST.getlist('users_selected', '')
        comment = request.POST.get('comment', '')

        try:
            if not validate(request, user=users_selected):
                raise AddError('没有某用户权限')
            if '' in [group_name]:
                error = u'组名不能为空'
                raise AddError(error)

            db_add_group(name=group_name, users=users_selected, dept=dept, comment=comment)
        except AddError:
            pass
        except TypeError:
            error = u'保存小组失败'
        else:
            msg = u'添加组 %s 成功' % group_name

    return render_to_response('juser/group_add.html', locals(), context_instance=RequestContext(request))


@require_super_user
def group_list(request):
    header_title, path1, path2 = '查看小组', '用户管理', '查看小组'
    keyword = request.GET.get('search', '')
    did = request.GET.get('did', '')
    contact_list = UserGroup.objects.all().order_by('name')

    if did:
        dept = DEPT.objects.filter(id=did)
        if dept:
            dept = dept[0]
            contact_list = dept.usergroup_set.all()

    if keyword:
        contact_list = contact_list.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)
    return render_to_response('juser/group_list.html', locals(), context_instance=RequestContext(request))


@require_admin
def group_list_adm(request):
    header_title, path1, path2 = '查看部门小组', '用户管理', '查看小组'
    keyword = request.GET.get('search', '')
    did = request.GET.get('did', '')
    user, dept = get_session_user_dept(request)
    contact_list = dept.usergroup_set.all().order_by('name')

    if keyword:
        contact_list = contact_list.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)
    return render_to_response('juser/group_list.html', locals(), context_instance=RequestContext(request))


@require_admin
def group_detail(request):
    group_id = request.GET.get('id', None)
    if not group_id:
        return HttpResponseRedirect('/')
    group = UserGroup.objects.get(id=group_id)
    users = group.user_set.all()
    return render_to_response('juser/group_detail.html', locals(), context_instance=RequestContext(request))


@require_super_user
def group_del(request):
    group_id = request.GET.get('id', '')
    if not group_id:
        return HttpResponseRedirect('/')
    UserGroup.objects.filter(id=group_id).delete()
    return HttpResponseRedirect('/juser/group_list/')


@require_admin
def group_del_adm(request):
    group_id = request.GET.get('id', '')
    if not validate(request, user_group=[group_id]):
        return HttpResponseRedirect('/juser/group_list/')
    if not group_id:
        return HttpResponseRedirect('/')
    UserGroup.objects.filter(id=group_id).delete()
    return HttpResponseRedirect('/juser/group_list/')


@require_admin
def group_del_ajax(request):
    group_ids = request.POST.get('group_ids')
    group_ids = group_ids.split(',')
    if request.session.get('role_id') == 1:
        if not validate(request, user_group=group_ids):
            return "error"
    for group_id in group_ids:
        UserGroup.objects.filter(id=group_id).delete()
    return HttpResponse('删除成功')


def group_update_member(group_id, users_id_list):
    group = UserGroup.objects.filter(id=group_id)
    if group:
        group = group[0]
        group.user_set.clear()
        for user_id in users_id_list:
            user = User.objects.get(id=user_id)
            group.user_set.add(user)


@require_super_user
def group_edit(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '修改小组信息', '用户管理', '编辑小组'
    if request.method == 'GET':
        group_id = request.GET.get('id', '')
        group = UserGroup.objects.filter(id=group_id)
        if group:
            group = group[0]
            dept_all = DEPT.objects.all()
            users_all = User.objects.all()
            users_selected = group.user_set.all()
            users = [user for user in users_all if user not in users_selected]

        return render_to_response('juser/group_edit.html', locals(), context_instance=RequestContext(request))
    else:
        group_id = request.POST.get('group_id', '')
        group_name = request.POST.get('group_name', '')
        dept_id = request.POST.get('dept_id', '')
        comment = request.POST.get('comment', '')
        users_selected = request.POST.getlist('users_selected')

        users = []
        try:
            if '' in [group_id, group_name]:
                raise AddError('组名不能为空')
            dept = DEPT.objects.filter(id=dept_id)
            if dept:
                dept = dept[0]
            else:
                raise AddError('部门不存在')
            for user_id in users_selected:
                users.extend(User.objects.filter(id=user_id))

            user_group = UserGroup.objects.filter(id=group_id)
            if user_group:
                user_group.update(name=group_name, comment=comment, dept=dept)
                user_group = user_group[0]
                user_group.user_set.clear()
                user_group.user_set = users

        except AddError, e:
            error = e

        return HttpResponseRedirect('/juser/group_list/')


@require_admin
def group_edit_adm(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '修改小组信息', '用户管理', '编辑小组'
    user, dept = get_session_user_dept(request)
    if request.method == 'GET':
        group_id = request.GET.get('id', '')
        if not validate(request, user_group=[group_id]):
            return HttpResponseRedirect('/juser/group_list/')
        group = UserGroup.objects.filter(id=group_id)
        if group:
            group = group[0]
            users_all = dept.user_set.all()
            users_selected = group.user_set.all()
            users = [user for user in users_all if user not in users_selected]

        return render_to_response('juser/group_edit.html', locals(), context_instance=RequestContext(request))
    else:
        group_id = request.POST.get('group_id', '')
        group_name = request.POST.get('group_name', '')
        comment = request.POST.get('comment', '')
        users_selected = request.POST.getlist('users_selected')

        users = []
        try:
            if not validate(request, user=users_selected):
                raise AddError(u'右侧非部门用户')

            if not validate(request, user_group=[group_id]):
                raise AddError(u'没有权限修改本组')

            for user_id in users_selected:
                users.extend(User.objects.filter(id=user_id))

            user_group = UserGroup.objects.filter(id=group_id)
            if user_group:
                user_group.update(name=group_name, comment=comment, dept=dept)
                user_group = user_group[0]
                user_group.user_set.clear()
                user_group.user_set = users

        except AddError, e:
            error = e

        return HttpResponseRedirect('/juser/group_list/')


@require_super_user
def user_add(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '添加用户', '用户管理', '添加用户'
    user_role = {'SU': u'超级管理员', 'DA': u'部门管理员', 'CU': u'普通用户'}
    dept_all = DEPT.objects.all()
    group_all = UserGroup.objects.all()

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        dept_id = request.POST.get('dept_id')
        groups = request.POST.getlist('groups', [])
        role_post = request.POST.get('role', 'CU')
        ssh_key_pwd = request.POST.get('ssh_key_pwd', '')
        is_active = True if request.POST.get('is_active', '1') == '1' else False
        ldap_pwd = gen_rand_pwd(16)

        try:
            if '' in [username, password, ssh_key_pwd, name, groups, role_post, is_active]:
                error = u'带*内容不能为空'
                raise AddError
            user = User.objects.filter(username=username)
            if user:
                error = u'用户 %s 已存在' % username
                raise AddError

            dept = DEPT.objects.filter(id=dept_id)
            if dept:
                dept = dept[0]
            else:
                error = u'部门不存在'
                raise AddError(error)

        except AddError:
            pass
        else:
            try:
                db_add_user(username=username,
                            password=md5_crypt(password),
                            name=name, email=email, dept=dept,
                            groups=groups, role=role_post,
                            ssh_key_pwd=CRYPTOR.encrypt(ssh_key_pwd),
                            ldap_pwd=CRYPTOR.encrypt(ldap_pwd),
                            is_active=is_active,
                            date_joined=datetime.datetime.now())

                server_add_user(username, password, ssh_key_pwd)
                if LDAP_ENABLE:
                    ldap_add_user(username, ldap_pwd)
                msg = u'添加用户 %s 成功！' % username

            except Exception, e:
                error = u'添加用户 %s 失败 %s ' % (username, e)
                try:
                    db_del_user(username)
                    server_del_user(username)
                    if LDAP_ENABLE:
                        ldap_del_user(username)
                except Exception:
                    pass
    return render_to_response('juser/user_add.html', locals(), context_instance=RequestContext(request))


@require_admin
def user_add_adm(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '添加用户', '用户管理', '添加用户'
    user, dept = get_session_user_dept(request)
    group_all = dept.usergroup_set.all()

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        groups = request.POST.getlist('groups', [])
        ssh_key_pwd = request.POST.get('ssh_key_pwd', '')
        is_active = True if request.POST.get('is_active', '1') == '1' else False
        ldap_pwd = gen_rand_pwd(16)

        try:
            if '' in [username, password, ssh_key_pwd, name, groups, is_active]:
                error = u'带*内容不能为空'
                raise AddError
            user = User.objects.filter(username=username)
            if user:
                error = u'用户 %s 已存在' % username
                raise AddError

        except AddError:
            pass
        else:
            try:
                db_add_user(username=username,
                            password=md5_crypt(password),
                            name=name, email=email, dept=dept,
                            groups=groups, role='CU',
                            ssh_key_pwd=CRYPTOR.encrypt(ssh_key_pwd),
                            ldap_pwd=CRYPTOR.encrypt(ldap_pwd),
                            is_active=is_active,
                            date_joined=datetime.datetime.now())

                server_add_user(username, password, ssh_key_pwd)
                if LDAP_ENABLE:
                    ldap_add_user(username, ldap_pwd)
                msg = u'添加用户 %s 成功！' % username

            except Exception, e:
                error = u'添加用户 %s 失败 %s ' % (username, e)
                try:
                    db_del_user(username)
                    server_del_user(username)
                    if LDAP_ENABLE:
                        ldap_del_user(username)
                except Exception:
                    pass
    return render_to_response('juser/user_add.html', locals(), context_instance=RequestContext(request))


@require_super_user
def user_list(request):
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    header_title, path1, path2 = '查看用户', '用户管理', '用户列表'
    keyword = request.GET.get('keyword', '')
    gid = request.GET.get('gid', '')
    did = request.GET.get('did', '')
    contact_list = User.objects.all().order_by('name')

    if gid:
        user_group = UserGroup.objects.filter(id=gid)
        if user_group:
            user_group = user_group[0]
            contact_list = user_group.user_set.all()

    if did:
        dept = DEPT.objects.filter(id=did)
        if dept:
            dept = dept[0]
            contact_list = dept.user_set.all().order_by('name')

    if keyword:
        contact_list = contact_list.filter(Q(username__icontains=keyword) | Q(name__icontains=keyword)).order_by('name')

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)

    return render_to_response('juser/user_list.html', locals(), context_instance=RequestContext(request))


@require_admin
def user_list_adm(request):
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    header_title, path1, path2 = '查看用户', '用户管理', '用户列表'
    keyword = request.GET.get('keyword', '')
    user, dept = get_session_user_dept(request)
    gid = request.GET.get('gid', '')
    contact_list = dept.user_set.all().order_by('name')

    if gid:
        if not validate(request, user_group=[gid]):
            return HttpResponseRedirect('/juser/user_list/')
        user_group = UserGroup.objects.filter(id=gid)
        if user_group:
            user_group = user_group[0]
            contact_list = user_group.user_set.all()

    if keyword:
        contact_list = contact_list.filter(Q(username__icontains=keyword) | Q(name__icontains=keyword)).order_by('name')

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(contact_list, request)

    return render_to_response('juser/user_list.html', locals(), context_instance=RequestContext(request))


@require_login
def user_detail(request):
    header_title, path1, path2 = '查看用户', '用户管理', '用户详情'
    if request.session.get('role_id') == 0:
        user_id = request.session.get('user_id')
    else:
        user_id = request.GET.get('id', '')
        if request.session.get('role_id') == 1:
            user, dept = get_session_user_dept(request)
            if not validate(request, user=[user_id]):
                return HttpResponseRedirect('/')
    if not user_id:
        return HttpResponseRedirect('/juser/user_list/')

    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        asset_group_permed = user_perm_group_api(user)
        logs_last = Log.objects.filter(user=user.name).order_by('-start_time')[0:10]
        logs_all = Log.objects.filter(user=user.name).order_by('-start_time')

    return render_to_response('juser/user_detail.html', locals(), context_instance=RequestContext(request))


@require_admin
def user_del(request):
    user_id = request.GET.get('id', '')
    if not user_id:
        return HttpResponseRedirect('/juser/user_list/')

    if request.session.get('role_id', '') == '1':
        if not validate(request, user=[user_id]):
            return HttpResponseRedirect('/juser/user_list/')

    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        user.delete()
        server_del_user(user.username)
        if LDAP_ENABLE:
            ldap_del_user(user.username)
    return HttpResponseRedirect('/juser/user_list/')


@require_admin
def user_del_ajax(request):
    user_ids = request.POST.get('ids')
    user_ids = user_ids.split(',')
    if request.session.get('role_id', '') == 1:
        if not validate(request, user=user_ids):
            return "error"
    for user_id in user_ids:
        user = User.objects.filter(id=user_id)
        if user:
            user = user[0]
            user.delete()
            server_del_user(user.username)
            if LDAP_ENABLE:
                ldap_del_user(user.username)

    return HttpResponse('删除成功')


@require_super_user
def user_edit(request):
    header_title, path1, path2 = '编辑用户', '用户管理', '用户编辑'
    if request.method == 'GET':
        user_id = request.GET.get('id', '')
        if not user_id:
            return HttpResponseRedirect('/')

        user_role = {'SU': u'超级管理员', 'DA': u'部门管理员', 'CU': u'普通用户'}
        user = User.objects.filter(id=user_id)
        dept_all = DEPT.objects.all()
        group_all = UserGroup.objects.all()
        if user:
            user = user[0]
            groups_str = ' '.join([str(group.id) for group in user.group.all()])

    else:
        user_id = request.POST.get('user_id', '')
        password = request.POST.get('password', '')
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        dept_id = request.POST.get('dept_id')
        groups = request.POST.getlist('groups', [])
        role_post = request.POST.get('role', 'CU')
        ssh_key_pwd = request.POST.get('ssh_key_pwd', '')
        is_active = True if request.POST.get('is_active', '1') == '1' else False

        user_role = {'SU': u'超级管理员', 'DA': u'部门管理员', 'CU': u'普通用户'}
        dept = DEPT.objects.filter(id=dept_id)
        if dept:
            dept = dept[0]
        else:
            dept = DEPT.objects.get(id='2')

        if user_id:
            user = User.objects.filter(id=user_id)
            if user:
                user = user[0]
        else:
            return HttpResponseRedirect('/juser/user_list/')

        if password != user.password:
            password = md5_crypt(password)

        if ssh_key_pwd != user.ssh_key_pwd:
            gen_ssh_key(user.username, ssh_key_pwd)
            ssh_key_pwd = CRYPTOR.encrypt(ssh_key_pwd)

        db_update_user(user_id=user_id,
                       password=password,
                       name=name,
                       email=email,
                       groups=groups,
                       dept=dept,
                       role=role_post,
                       is_active=is_active,
                       ssh_key_pwd=ssh_key_pwd)

        return HttpResponseRedirect('/juser/user_list/')

    return render_to_response('juser/user_edit.html', locals(), context_instance=RequestContext(request))


@require_admin
def user_edit_adm(request):
    header_title, path1, path2 = '编辑用户', '用户管理', '用户编辑'
    user, dept = get_session_user_dept(request)
    if request.method == 'GET':
        user_id = request.GET.get('id', '')
        if not user_id:
            return HttpResponseRedirect('/juser/user_list/')

        if not validate(request, user=[user_id]):
            return HttpResponseRedirect('/juser/user_list/')

        user = User.objects.filter(id=user_id)
        dept_all = DEPT.objects.all()
        group_all = dept.usergroup_set.all()
        if user:
            user = user[0]
            groups_str = ' '.join([str(group.id) for group in user.group.all()])

    else:
        user_id = request.POST.get('user_id', '')
        password = request.POST.get('password', '')
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        groups = request.POST.getlist('groups', [])
        ssh_key_pwd = request.POST.get('ssh_key_pwd', '')
        is_active = True if request.POST.get('is_active', '1') == '1' else False

        if not validate(request, user=[user_id], user_group=groups):
            return HttpResponseRedirect('/juser/user_edit/')
        if user_id:
            user = User.objects.filter(id=user_id)
            if user:
                user = user[0]
        else:
            return HttpResponseRedirect('/juser/user_list/')

        if password != user.password:
            password = md5_crypt(password)

        if ssh_key_pwd != user.ssh_key_pwd:
            ssh_key_pwd = CRYPTOR.encrypt(ssh_key_pwd)

        db_update_user(user_id=user_id,
                       password=password,
                       name=name,
                       email=email,
                       groups=groups,
                       is_active=is_active,
                       ssh_key_pwd=ssh_key_pwd)

        return HttpResponseRedirect('/juser/user_list/')

    return render_to_response('juser/user_edit.html', locals(), context_instance=RequestContext(request))


def profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return HttpResponseRedirect('/')
    user = User.objects.get(id=user_id)
    return render_to_response('juser/profile.html', locals(), context_instance=RequestContext(request))


def chg_info(request):
    header_title, path1, path2 = '修改信息', '用户管理', '修改个人信息'
    user_id = request.session.get('user_id')
    user_set = User.objects.filter(id=user_id)
    error = ''
    if user_set:
        user = user_set[0]
    else:
        return HttpResponseRedirect('/')

    if request.method == 'POST':
        name = request.POST.get('name', '')
        password = request.POST.get('password', '')
        ssh_key_pwd = request.POST.get('ssh_key_pwd', '')
        email = request.POST.get('email', '')

        if '' in [name, password, ssh_key_pwd, email]:
            error = '不能为空'

        if len(password) < 6 or len(ssh_key_pwd) < 6:
            error = '密码须大于6位'

        if not error:
            if password != user.password:
                password = md5_crypt(password)

            if ssh_key_pwd != user.ssh_key_pwd:
                gen_ssh_key(user.username, ssh_key_pwd)
                ssh_key_pwd = md5_crypt(ssh_key_pwd)

            user_set.update(name=name, password=password, ssh_key_pwd=ssh_key_pwd, email=email)
            msg = '修改成功'

    return render_to_response('juser/chg_info.html', locals(), context_instance=RequestContext(request))





@require_login
def down_key(request):
    user_id = ''
    if is_super_user(request):
        user_id = request.GET.get('id')

    if is_group_admin(request):
        user_id = request.GET.get('id')
        if not validate(request, user=[user_id]):
            user_id = request.session.get('user_id')

    if is_common_user(request):
        user_id = request.session.get('user_id')

    if user_id:
        user = User.objects.filter(id=user_id)
        if user:
            user = user[0]
            username = user.username
            private_key_dir = os.path.join(BASE_DIR, 'keys/jumpserver/')
            private_key_file = os.path.join(private_key_dir, username+".pem")
            if os.path.isfile(private_key_file):
                f = open(private_key_file)
                data = f.read()
                f.close()
                response = HttpResponse(data, content_type='application/octet-stream')
                response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(private_key_file)
                return response

    return HttpResponse('No Key File. Contact Admin.')