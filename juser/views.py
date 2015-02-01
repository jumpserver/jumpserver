# coding: utf-8
# Author: Guanghongwei
# Email: ibuler@qq.com

import time
import os
import random
import subprocess
import ldap
from ldap import modlist
from Crypto.PublicKey import RSA
import crypt
from django.http import HttpResponseRedirect

from django.shortcuts import render_to_response
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, InvalidPage

from juser.models import UserGroup, User
from connect import PyCrypt, KEY
from connect import BASE_DIR
from connect import CONF
from jumpserver.views import md5_crypt


CRYPTOR = PyCrypt(KEY)
LDAP_ENABLE = CONF.getint('ldap', 'ldap_enable')
if LDAP_ENABLE:
    LDAP_HOST_URL = CONF.get('ldap', 'host_url')
    LDAP_BASE_DN = CONF.get('ldap', 'base_dn')
    LDAP_ROOT_DN = CONF.get('ldap', 'root_dn')
    LDAP_ROOT_PW = CONF.get('ldap', 'root_pw')


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


class LDAPMgmt():
    def __init__(self,
                 host_url,
                 base_dn,
                 root_cn,
                 root_pw):
        self.ldap_host = host_url
        self.ldap_base_dn = base_dn
        self.conn = ldap.initialize(host_url)
        self.conn.set_option(ldap.OPT_REFERRALS, 0)
        self.conn.protocol_version = ldap.VERSION3
        self.conn.simple_bind_s(root_cn, root_pw)

    def list(self, filter, scope=ldap.SCOPE_SUBTREE, attr=None):
        result = {}
        try:
            ldap_result = self.conn.search_s(self.ldap_base_dn, scope, filter, attr)
            for entry in ldap_result:
                name, data = entry
                for k, v in data.items():
                    print '%s: %s' % (k, v)
                    result[k] = v
            return result
        except ldap.LDAPError, e:
            print e

    def add(self, dn, attrs):
        try:
            ldif = modlist.addModlist(attrs)
            self.conn.add_s(dn, ldif)
        except ldap.LDAPError, e:
            print e

    def modify(self, dn, attrs):
        try:
            attr_s = []
            for k, v in attrs.items():
                attr_s.append((2, k, v))
            self.conn.modify_s(dn, attr_s)
        except ldap.LDAPError, e:
            print e

    def delete(self, dn):
        try:
            self.conn.delete_s(dn)
        except ldap.LDAPError, e:
            print e


def gen_sha512(salt, password):
    return crypt.crypt(password, '$6$%s$' % salt)


def group_db_add(**kwargs):
    group_name = kwargs.get('name')
    group = UserGroup.objects.filter(name=group_name)
    if group:
        raise AddError('Group %s have been exist .' % group_name)
    UserGroup.objects.create(**kwargs)


def group_add_user(group_name, user_id=None, username=None):
    try:
        if user_id:
            user = User.objects.get(id=user_id)
        else:
            user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        raise AddError('用户获取失败')
    else:
        group = UserGroup.objects.get(name=group_name)
        group.user_set.add(user)


def group_update_user(group_id, users_id):
    group = UserGroup.objects.get(id=group_id)
    group.user_set.clear()
    for user_id in users_id:
        user = User.objects.get(id=user_id)
        group.user_set.add(user)


def db_add_user(**kwargs):
    groups_post = kwargs.pop('groups')
    user = User(**kwargs)
    group_select = []
    for group_id in groups_post:
        group = UserGroup.objects.filter(id=group_id)
        group_select.extend(group)
    user.save()
    user.user_group = group_select


def db_update_user(**kwargs):
    groups_post = kwargs.pop('groups')
    username = kwargs.get('username')
    user = User.objects.filter(username=username)
    user.update(**kwargs)
    user = User.objects.get(username=username)
    group_select = []
    for group_id in groups_post:
        group = UserGroup.objects.filter(id=group_id)
        group_select.extend(group)
    user.save()
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
    user = User.objects.get(username=username)

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

    sudo_dn = 'cn=%s,ou=Sudoers,%s' % (username, LDAP_BASE_DN)
    sudo_attr = {'objectClass': ['top', 'sudoRole'],
                 'cn': ['%s' % str(username)],
                 'sudoCommand': ['/bin/pwd'],
                 'sudoHost': ['192.168.1.1'],
                 'sudoOption': ['!authenticate'],
                 'sudoRunAsUser': ['root'],
                 'sudoUser': ['%s' % str(username)]}

    ldap_conn = LDAPMgmt(LDAP_HOST_URL, LDAP_BASE_DN, LDAP_ROOT_DN, LDAP_ROOT_PW)

    ldap_conn.add(user_dn, user_attr)
    ldap_conn.add(group_dn, group_attr)
    ldap_conn.add(sudo_dn, sudo_attr)


def ldap_del_user(username):
    user_dn = "uid=%s,ou=People,%s" % (username, LDAP_BASE_DN)
    group_dn = "cn=%s,ou=Group,%s" % (username, LDAP_BASE_DN)
    sudo_dn = 'cn=%s,ou=Sudoers,%s' % (username, LDAP_BASE_DN)

    ldap_conn = LDAPMgmt(LDAP_HOST_URL, LDAP_BASE_DN, LDAP_ROOT_DN, LDAP_ROOT_PW)
    ldap_conn.delete(user_dn)
    ldap_conn.delete(group_dn)
    ldap_conn.delete(sudo_dn)


def group_add(request, group_type_select='A'):
    error = ''
    msg = ''
    header_title, path1, path2 = '添加属组 | Add Group', 'juser', 'group_add'
    group_types = {
        # 'P': '私有组',
        'M': '部门',
        'A': '用户组',
    }

    users_all = User.objects.all()
    if group_type_select == 'M':
        users = [user for user in users_all if not user.user_group.filter(type='M')]
    else:
        users = users_all

    if request.method == 'POST':
        group_name = request.POST.get('group_name', '')
        group_type = request.POST.get('group_type', 'A')
        users_selected = request.POST.getlist('users_selected', '')
        comment = request.POST.get('comment', '')

        try:
            if not group_name:
                error = u'组名不能为空'
                raise AddError
            group_db_add(name=group_name, comment=comment, type=group_type)
            for user_id in users_selected:
                group_add_user(group_name, user_id=user_id)

        except AddError:
            pass
        except TypeError:
            error = u'保存用户组失败'
        else:
            msg = u'添加组 %s 成功' % group_name

    return render_to_response('juser/group_add.html', locals())


def group_add_ajax(request):
    group_type = request.POST.get('type', 'A')
    users_all = User.objects.all()
    if group_type == 'A':
        users = users_all
    else:
        users = [user for user in users_all if not user.user_group.filter(type='M')]

    return render_to_response('juser/group_add_ajax.html', locals())


def group_list(request):
    header_title, path1, path2 = '查看属组 | Show Group', 'juser', 'group_list'
    groups = contact_list = UserGroup.objects.filter(Q(type='M') | Q(type='A')).order_by('type')
    p = paginator = Paginator(contact_list, 10)

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts = paginator.page(page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)
    return render_to_response('juser/group_list.html', locals())


def group_detail(request):
    group_id = request.GET.get('id', None)
    if not group_id:
        return HttpResponseRedirect('/')
    group = UserGroup.objects.get(id=group_id)
    users = group.user_set.all()
    return render_to_response('juser/group_detail.html', locals())


def group_del(request):
    group_id = request.GET.get('id', None)
    if not group_id:
        return HttpResponseRedirect('/')
    group = UserGroup.objects.get(id=group_id)
    group.delete()
    return HttpResponseRedirect('/juser/group_list/', locals())


def group_edit(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '修改属组 | Edit Group', 'juser', 'group_edit'
    group_types = {
        # 'P': '私有组',
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

        return render_to_response('juser/group_edit.html', locals())
    else:
        group_id = request.POST.get('group_id', None)
        group_name = request.POST.get('group_name', None)
        comment = request.POST.get('comment', '')
        users_selected = request.POST.getlist('users_selected')
        group_type = request.POST.get('group_type')
        group = UserGroup.objects.filter(id=group_id)
        # return HttpResponse(group_type)
        group.update(name=group_name, comment=comment, type=group_type)
        group_update_user(group_id, users_selected)

        return HttpResponseRedirect('/juser/group_list/')


def user_list(request):
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    header_title, path1, path2 = '查看用户 | Show User', 'juser', 'user_list'
    users = contact_list = User.objects.all().order_by('id')
    p = paginator = Paginator(contact_list, 10)

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts = paginator.page(page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)
    return render_to_response('juser/user_list.html', locals())


def user_detail(request):
    user_id = request.GET.get('id', None)
    if not user_id:
        return HttpResponseRedirect('/')
    user = User.objects.get(id=user_id)
    return render_to_response('juser/user_detail.html', locals())


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
    return HttpResponseRedirect('/juser/user_list/', locals())


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

    return render_to_response('juser/user_add.html', locals())


def user_add(request):
    error = ''
    msg = ''
    header_title, path1, path2 = '添加用户 | Add User', 'juser', 'user_add'
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    manage_groups = UserGroup.objects.filter(type='M')
    auth_groups = UserGroup.objects.filter(type='A')
    if request.method == 'POST':
        username = request.POST.get('username', None)
        password = request.POST.get('password', '')
        name = request.POST.get('name', None)
        email = request.POST.get('email', '')
        manage_group_id = request.POST.get('manage_group')
        auth_groups = request.POST.getlist('groups', None)
        groups = auth_groups
        groups.append(manage_group_id)
        groups_str = ' '.join(auth_groups)
        role_post = request.POST.get('role', 'CU')
        ssh_pwd = request.POST.get('ssh_pwd', '')
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

        except AddError:
            pass
        else:
            time_now = time.time()
            try:
                db_add_user(username=username,
                            password=md5_crypt(password),
                            name=name, email=email,
                            groups=groups, role=role_post,
                            ssh_pwd=CRYPTOR.encrypt(ssh_pwd) if ssh_pwd else '',
                            ssh_key_pwd=CRYPTOR.encrypt(ssh_key_pwd),
                            ldap_pwd=CRYPTOR.encrypt(ldap_pwd),
                            is_active=is_active,
                            date_joined=time_now)

                server_add_user(username, password, ssh_key_pwd)
                group_db_add(name=username, comment=username, type='P')
                group_add_user(group_name=username, username=username)
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

    return render_to_response('juser/user_add.html', locals())







