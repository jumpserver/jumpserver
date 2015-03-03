# coding: utf-8
# Author: Guanghongwei
# Email: ibuler@qq.com

import time
import os
import random
import subprocess
from Crypto.PublicKey import RSA
import crypt
from django.http import HttpResponseRedirect
import datetime

from django.shortcuts import render_to_response
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template import RequestContext
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, InvalidPage

from juser.models import UserGroup, User, DEPT
from connect import PyCrypt, KEY
from connect import BASE_DIR
from connect import CONF
from jumpserver.views import md5_crypt, LDAPMgmt, LDAP_ENABLE, ldap_conn, page_list_return

if LDAP_ENABLE:
    LDAP_HOST_URL = CONF.get('ldap', 'host_url')
    LDAP_BASE_DN = CONF.get('ldap', 'base_dn')
    LDAP_ROOT_DN = CONF.get('ldap', 'root_dn')
    LDAP_ROOT_PW = CONF.get('ldap', 'root_pw')

CRYPTOR = PyCrypt(KEY)


def gen_rand_pwd(num):
    """生成随机密码"""
    seed = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    salt_list = []
    for i in range(num):
        salt_list.append(random.choice(seed))
    salt = ''.join(salt_list)
    return salt


def bash(cmd):
    """执行bash命令"""
    return subprocess.call(cmd, shell=True)


def is_dir(dir_name, mode=0755):
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
    os.chmod(dir_name, mode)


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





def group_update_user(group_id, users_id):
    group = UserGroup.objects.get(id=group_id)
    group.user_set.clear()
    for user_id in users_id:
        user = User.objects.get(id=user_id)
        group.user_set.add(user)


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
    groups_post = kwargs.pop('groups')
    username = kwargs.get('username')
    user = User.objects.filter(username=username)
    user.update(**kwargs)
    user = User.objects.get(username=username)
    user.save()

    if groups_post:
        group_select = []
        for group_id in groups_post:
            group = UserGroup.objects.filter(id=group_id)
            group_select.extend(group)
        user.user_group = group_select


def db_del_user(username):
    try:
        user = User.objects.get(username=username)
        user.delete()
    except ObjectDoesNotExist:
        pass


def gen_ssh_key(username, password=None, length=2048):
    private_key_dir = os.path.join(BASE_DIR, 'keys/jumpserver/')
    private_key_file = os.path.join(private_key_dir, username)
    public_key_dir = '/home/%s/.ssh/' % username
    public_key_file = os.path.join(public_key_dir, 'authorized_keys')
    is_dir(private_key_dir)
    is_dir(public_key_dir, mode=0700)

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
    bash('useradd %s; echo %s | passwd --stdin %s' % (username, password, username))
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


# def ldap_group_add(group_name, username_list, gid):
#     group_dn = "cn=%s,ou=Group,%s" % (group_name, LDAP_BASE_DN)
#     group_attr = {'objectClass': ['posixGroup', 'top'],
#                   'cn': [str(group_name)],
#                   'userPassword': ['{crypt}x'],
#                   'gidNumber': [gid],
#                   'memberUid': username_list}
#     ldap_conn.add(group_dn, group_attr)


# def group_add_ajax(request):
#     group_type = request.POST.get('type', 'A')
#     users_all = User.objects.all()
#     if group_type == 'A':
#         users = users_all
#     else:
#         users = [user for user in users_all if not user.user_group.filter(type='M')]
#
#     return render_to_response('juser/group_add_ajax.html', locals(), context_instance=RequestContext(request))


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


def dept_list(request):
    header_title, path1, path2 = '查看部门', '用户管理', '查看部门'
    keyword = request.GET.get('search')
    if keyword:
        contact_list = DEPT.objects.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword)).order_by('name')
    else:
        contact_list = DEPT.objects.all()
    p = paginator = Paginator(contact_list, 10)

    try:
        current_page = int(request.GET.get('page', '1'))
    except ValueError:
        current_page = 1

    page_range = page_list_return(len(p.page_range), current_page)

    try:
        contacts = paginator.page(current_page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)
    return render_to_response('juser/dept_list.html', locals(), context_instance=RequestContext(request))


def dept_detail(request):
    dept_id = request.GET.get('id', None)
    if not dept_id:
        return HttpResponseRedirect('/juser/dept_list/')
    dept = DEPT.objects.filter(id=dept_id)
    if dept:
        dept = dept[0]
        users = dept.user_set.all()
    return render_to_response('juser/dept_detail.html', locals(), context_instance=RequestContext(request))


def dept_del(request):
    dept_id = request.GET.get('id', None)
    if not dept_id:
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
        users = request.POST.get('users_selected', [])
        comment = request.POST.get('comment', '')

        dept = DEPT.objects.filter(id=dept_id)
        if dept:
            dept.update(name=name, comment=comment)
        else:
            error = '部门不存在'

    return render_to_response('juser/dept_edit.html', locals(), context_instance=RequestContext(request))


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

            dept = DEPT.objects.filter(id=dept_id)
            if dept:
                dept = dept[0]
            else:
                AddError(u'部门不存在')

            db_add_group(name=group_name, users=users_selected, dept=dept, comment=comment)
        except AddError:
            pass
        except TypeError:
            error = u'保存小组失败'
        else:
            msg = u'添加组 %s 成功' % group_name

    return render_to_response('juser/group_add.html', locals(), context_instance=RequestContext(request))


def group_list(request):
    header_title, path1, path2 = '查看小组', '用户管理', '查看小组'
    keyword = request.GET.get('search', '')
    if keyword:
        contact_list = UserGroup.objects.filter(Q(name__icontains=keyword) | Q(comment__icontains=keyword))
    else:
        contact_list = UserGroup.objects.all().order_by('name')
    p = paginator = Paginator(contact_list, 10)

    try:
        current_page = int(request.GET.get('page', '1'))
    except ValueError:
        current_page = 1

    page_range = page_list_return(len(p.page_range), current_page)

    try:
        contacts = paginator.page(current_page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)
    return render_to_response('juser/group_list.html', locals(), context_instance=RequestContext(request))


def group_detail(request):
    group_id = request.GET.get('id', None)
    if not group_id:
        return HttpResponseRedirect('/')
    group = UserGroup.objects.get(id=group_id)
    users = group.user_set.all()
    return render_to_response('juser/group_detail.html', locals(), context_instance=RequestContext(request))


def group_del(request):
    group_id = request.GET.get('id', None)
    if not group_id:
        return HttpResponseRedirect('/')
    group = UserGroup.objects.get(id=group_id)
    group.delete()
    return HttpResponseRedirect('/juser/group_list/', locals(), context_instance=RequestContext(request))


def group_edit(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '修改属组 | Edit Group', 'juser', 'group_edit'
    group_types = {
        'M': '部门',
        'A': '用户组',
    }
    if request.method == 'GET':
        group_id = request.GET.get('id', None)
        group = UserGroup.objects.get(id=group_id)
        group_name = group.name
        comment = group.comment
        group_type = group.type
        users_all = User.objects.all()
        users_selected = group.user_set.all()
        users = [user for user in users_all if user not in users_selected]

        return render_to_response('juser/group_edit.html', locals(), context_instance=RequestContext(request))
    else:
        group_id = request.POST.get('group_id', None)
        group_name = request.POST.get('group_name', None)
        comment = request.POST.get('comment', '')
        users_selected = request.POST.getlist('users_selected')
        group_type = request.POST.get('group_type')
        group = UserGroup.objects.filter(id=group_id)
        group.update(name=group_name, comment=comment, type=group_type)
        group_update_user(group_id, users_selected)

        return HttpResponseRedirect('/juser/group_list/')


def user_add(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '添加用户 | User Add', '用户管理', '添加用户'
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
        is_active = request.POST.get('is_active', '1')
        ldap_pwd = gen_rand_pwd(16)

        try:
            if None in [username, password, ssh_key_pwd, name, groups, role_post, is_active]:
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


def user_list(request):
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    header_title, path1, path2 = '查看用户', '用户管理', '用户列表'
    keyword = request.GET.get('search', '')
    if keyword:
        contact_list = User.objects.filter(Q(username__icontains=keyword) | Q(name__icontains=keyword)).order_by('name')
    else:
        contact_list = User.objects.all().order_by('id')
    p = paginator = Paginator(contact_list, 10)

    try:
        current_page = int(request.GET.get('page', '1'))
    except ValueError:
        current_page = 1

    page_range = page_list_return(len(p.page_range), current_page)

    try:
        contacts = paginator.page(current_page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)
    return render_to_response('juser/user_list.html', locals(), context_instance=RequestContext(request))


def user_detail(request):
    user_id = request.GET.get('id', None)
    if not user_id:
        return HttpResponseRedirect('/')
    user = User.objects.get(id=user_id)
    return render_to_response('juser/user_detail.html', locals(), context_instance=RequestContext(request))


def user_del(request):
    user_id = request.GET.get('id', None)
    if not user_id:
        return HttpResponseRedirect('/')
    user = User.objects.get(id=user_id)
    user.delete()
    group = UserGroup.objects.get(name=user.username)
    group.delete()
    server_del_user(user.username)
    ldap_del_user(user.username)
    return HttpResponseRedirect('/juser/user_list/', locals(), context_instance=RequestContext(request))


def user_edit(request):
    header_title, path1, path2 = '编辑用户 | Edit User', 'juser', 'user_edit'
    readonly = "readonly"
    if request.method == 'GET':
        user_id = request.GET.get('id', None)
        if not user_id:
            return HttpResponseRedirect('/')
        user = User.objects.get(id=user_id)
        username = user.username
        password = user.password
        ssh_key_pwd = user.ssh_key_pwd
        name = user.name
        manage_groups = UserGroup.objects.filter(type='M')
        auth_groups = UserGroup.objects.filter(type='A')
        manage_group_id = user.user_group.get(type='M').id
        groups_str = ' '.join([str(group.id) for group in auth_groups])
        user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
        role_post = user.role
        ssh_pwd = user.ssh_pwd
        email = user.email

    else:
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        name = request.POST.get('name', None)
        email = request.POST.get('email', '')
        manage_group_id = request.POST.get('manage_group', '')
        auth_groups = request.POST.getlist('groups', None)
        groups = auth_groups
        groups.append(manage_group_id)
        groups_str = ' '.join(auth_groups)
        role_post = request.POST.get('role', None)
        ssh_pwd = request.POST.get('ssh_pwd', None)
        ssh_key_pwd = request.POST.get('ssh_key_pwd', None)
        is_active = request.POST.get('is_active', '1')
        ldap_pwd = gen_rand_pwd(16)
        all_group = UserGroup.objects.filter(Q(type='M') | Q(type='A'))
        user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}

        if username:
            user = User.objects.get(username=username)
        else:
            return HttpResponseRedirect('/')

        if password != user.password:
            password = md5_crypt(password)

        if ssh_pwd != user.ssh_pwd:
            ssh_pwd = CRYPTOR.encrypt(ssh_pwd)

        if ssh_key_pwd != user.ssh_key_pwd:
            ssh_key_pwd = CRYPTOR.encrypt(ssh_key_pwd)

        db_update_user(username=username,
                       password=password,
                       name=name,
                       email=email,
                       groups=groups,
                       role=role_post,
                       ssh_pwd=ssh_pwd,
                       ssh_key_pwd=ssh_key_pwd)
        msg = u'修改用户成功'

        return HttpResponseRedirect('/juser/user_list/')

    return render_to_response('juser/user_add.html', locals(), context_instance=RequestContext(request))


def profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return HttpResponseRedirect('/')
    user = User.objects.get(id=user_id)
    return render_to_response('juser/user_detail.html', locals(), context_instance=RequestContext(request))


def chg_pass(request):
    header_title, path1, path2 = '修改信息 | Edit Info', '用户管理', '修改个人信息'

    return render_to_response('juser/user_add.html', locals(), context_instance=RequestContext(request))

