#coding: utf-8

from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from UserManage.models import User, Group
from Assets.models import Assets, AssetsUser
import subprocess
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import random
import ConfigParser
import os
import ldap
import ldap.modlist as modlist
import crypt
import hashlib
from UserManage.forms import UserAddForm, GroupAddForm


base_dir = "/opt/jumpserver/"
cf = ConfigParser.ConfigParser()
cf.read('%s/jumpserver.conf' % base_dir)

key = cf.get('jumpserver', 'key')
rsa_dir = cf.get('jumpserver', 'rsa_dir')
useradd_shell = cf.get('jumpserver', 'useradd_shell')
userdel_shell = cf.get('jumpserver', 'userdel_shell')
sudoadd_shell = cf.get('jumpserver', 'sudoadd_shell')
sudodel_shell = cf.get('jumpserver', 'sudodel_shell')
keygen_shell = cf.get('jumpserver', 'keygen_shell')
chgpass_shell = cf.get('jumpserver', 'chgpass_shell')
admin = ['admin']
ldap_host = cf.get('jumpserver', 'ldap_host')
ldap_base_dn = cf.get('jumpserver', 'ldap_base_dn')
admin_cn = cf.get('jumpserver', 'admin_cn')
admin_pass = cf.get('jumpserver', 'admin_pass')


def keygen(num):
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


def md5_crypt(string):
    return hashlib.new("md5", string).hexdigest()


class PyCrypt(object):
    """对称加密解密"""
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, b'0000000000000000')
        length = 16
        count = len(text)
        if count < length:
            add = (length - count)
            text += ('\0' * add)
        elif count > length:
            add = (length - (count % length))
            text += ('\0' * add)
        ciphertext = cryptor.encrypt(text)
        return b2a_hex(ciphertext)

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, b'0000000000000000')
        plain_text = cryptor.decrypt(a2b_hex(text))
        return plain_text.rstrip('\0')


def rsa_gen(username, key_pass, rsa_dir=rsa_dir):
    rsa_file = '%s/%s' % (rsa_dir, username)
    pub_file = '%s.pub' % rsa_file
    authorized_file = '/home/%s/.ssh/authorized_keys' % username
    if os.path.exists(rsa_file):
        os.unlink(rsa_file)
    ret = bash('ssh-keygen -t rsa -f %s -P %s &> /dev/null && echo "######## rsa_gen Ok."' % (rsa_file, key_pass))
    if not ret:
        try:
            if not os.path.isdir('/home/%s/.ssh' % username):
                os.mkdir('/home/%s/.ssh' % username)
            pub = open(pub_file, 'r')
            authorized = open(authorized_file, 'w')
            authorized.write(pub.read())
            pub.close()
            authorized.close()
        except Exception:
            return 1
        else:
            return 0


class LDAPMgmt():
    def __init__(self,
                 ldap_host=ldap_host,
                 ldap_base_dn=ldap_base_dn,
                 admin_cn=admin_cn,
                 admin_pass=admin_pass):
        self.ldap_host = ldap_host
        self.ldap_base_dn = ldap_base_dn
        self.admin_cn = admin_cn
        self.admin_pass = admin_pass
        self.conn = ldap.initialize(ldap_host)
        self.conn.set_option(ldap.OPT_REFERRALS, 0)
        self.conn.protocol_version = ldap.VERSION3
        self.conn.simple_bind_s(admin_cn, admin_pass)

    def list(self, filter, scope=ldap.SCOPE_SUBTREE, attr=None):
        try:
            ldap_result = self.conn.search_s(self.ldap_base_dn, scope, filter, attr)
            print 'Here is the result: '
            for entry in ldap_result:
                name, data = entry
                print '#'*20, name, '#'*20
                for k, v in data.items():
                    print '%s: %s' % (k,v)
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


def group_member(username):
    member = []
    user = User.objects.get(username=username)
    for group in user.group.all():
        member.extend(group.user_set.all())
    return list(set(member))


def user_assets(username):
    assets = []
    user = User.objects.get(username=username)
    for asset in user.assetsuser_set.all():
        assets.append(asset.aid)
    return assets


def login_required(func):
    """要求登录的装饰器"""
    def _deco(request, *args, **kwargs):
        if not request.session.get('username'):
            return HttpResponseRedirect('/login/')
        return func(request, *args, **kwargs)
    return _deco


def admin_required(func):
    """要求用户是admin的装饰器"""
    def _deco(request, *args, **kwargs):
        if not request.session.get('admin'):
            return HttpResponseRedirect('/')
        return func(request, *args, **kwargs)
    return _deco


def superuser_required(func):
    """要求用户是superuser"""
    def _deco(request, *args, **kwargs):
        if request.session.get('admin') != 2:
            return HttpResponseRedirect('/')
        return func(request, *args, **kwargs)
    return _deco


def is_admin_user(request):
    if request.session.get('admin') == 1:
        return True
    else:
        return False


def is_super_user(request):
    if request.session.get('admin') == 2:
        return True
    else:
        return False


def install(request):
    user = User.objects.filter(username='admin')
    if user:
        return HttpResponseRedirect('/login/')
    else:
        u = User(
            username='admin',
            password=md5_crypt('admin'),
            key_pass=md5_crypt('admin'),
            name='admin',
            is_admin=False,
            is_superuser=True,
            ldap_password=md5_crypt('admin'))
        u.save()
        return HttpResponse('Install successfully, please refresh this page.')


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
                request.session['username'] = username
                if user.is_admin:
                    request.session['admin'] = 1
                elif user.is_superuser:
                    request.session['admin'] = 2
                else:
                    request.session['admin'] = 0
                return HttpResponseRedirect('/')
            else:
                error = '密码错误，请重新输入。'
        else:
            error = '用户不存在。'
    return render_to_response('login.html', {'error': error})


def logout(request):
    """注销登录调用"""
    if request.session.get('username'):
        del request.session['username']
        del request.session['admin']
    return HttpResponseRedirect('/login/')


@login_required
def downKey(request):
    """下载key"""
    username = request.session.get('username')
    if request.session.get('admin') == 1:
        user = User.objects.get(username=username)
        if user in group_member(username):
            username = request.GET.get('username')
    elif request.session.get('admin') == 2:
        username = request.GET.get('username')

    filename = '%s/keys/%s' % (base_dir, username)
    f = open(filename)
    data = f.read()
    f.close()
    response = HttpResponse(data, content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename=%s.rsa' % username
    return response


@login_required
def index(request):
    """主页"""
    username = request.session.get('username')
    name = User.objects.filter(username=username)
    assets = []
    if name:
        user_assets = AssetsUser.objects.filter(uid=name[0])
        if user_assets:
            for user_asset in user_assets:
                assets.append(user_asset.aid)
    return render_to_response('index.html', {'index': 'active', 'assets': assets},
                              context_instance=RequestContext(request))


@admin_required
def showUser(request):
    """查看所有用户"""
    info = ''
    error = ''

    if is_super_user(request):
        users = User.objects.all()
    else:
        users = group_member(request.session.get('username'))

    if request.method == 'POST':
        selected_user = request.REQUEST.getlist('selected')
        if selected_user:
            for user_id in selected_user:
                # 从数据库中删除
                try:
                    user = User.objects.get(id=user_id)
                    if user.is_admin or user.is_superuser:
                        if is_admin_user(request):
                            return HttpResponseRedirect('/showUser/')
                    username = user.username
                    user.delete()
                except Exception, e:
                    error = u'数据库中用户删除错误' + unicode(e)

                # 在bash中删除
                bash_del = bash("userdel -r %s" % username)
                if bash_del != 0:
                    error = u'bash中用户删除错误'

                # 从LDAP中删除
                try:
                    ldap_del = LDAPMgmt()
                    user_dn = "uid=%s,ou=People,%s" % (username, ldap_base_dn)
                    group_dn = "cn=%s,ou=Group,%s" % (username, ldap_base_dn)
                    ldap_del.delete(user_dn)
                    ldap_del.delete(group_dn)
                except Exception, e:
                    error = u'ldap中用户删除错误' + unicode(e)

                if not error:
                    info = '用户删除成功'

    return render_to_response('showUser.html',
                              {'users': users,
                               'info': info,
                               'error': error,
                               'user_menu': 'active'},
                              context_instance=RequestContext(request))


@admin_required
def addUser(request):
    """添加用户"""
    msg = ''
    form = UserAddForm()
    jm = PyCrypt(key)

    if request.method == 'POST':
        form = UserAddForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data
            username = user['username']
            password = user['password']
            key_pass = user['key_pass']
            name = user['name']
            is_admin = user['is_admin']
            is_superuser = user['is_superuser']
            ldap_password = keygen(16)
            group_post = user['group']
            groups = []

            # 如果用户是admin，那么不能委任其他admin或者超级用户
            if is_admin_user(request):
                is_admin = False
                is_superuser = False

            # 组
            for group_name in group_post:
                groups.append(Group.objects.get(name=group_name))

            # 数据中保存用户，如果失败就返回
            u = User(
                username=username,
                password=md5_crypt(password),
                key_pass=jm.encrypt(key_pass),
                name=name,
                is_admin=is_admin,
                is_superuser=is_superuser,
                ldap_password=jm.encrypt(ldap_password))
            try:
                u.save()
                u.group = groups
                u.save()
            except Exception, e:
                error = u'数据库插入用户错误' + unicode(e)
                return render_to_response('addUser.html', {'user_menu': 'active', 'form': form, 'error': error},
                                          context_instance=RequestContext(request))

            # 系统中添加用户
            ret_add = bash('useradd %s' % username)
            ret_passwd = bash('echo %s | passwd --stdin %s' % (password, username))
            ret_rsa = rsa_gen(username, key_pass)

            if [ret_add, ret_passwd, ret_rsa].count(0) < 3:
                error = u'跳板机添加用户失败'
                bash('userdel -r %s' % username)
                u.delete()
                return render_to_response('addUser.html', {'user_menu': 'active', 'form': form, 'error': error},
                                          context_instance=RequestContext(request))

            # 添加到ldap中
            user_dn = "uid=%s,ou=People,%s" % (username, ldap_base_dn)
            password_sha512 = gen_sha512(keygen(6), ldap_password)
            user_attr = {
                'uid': [str(username)],
                'cn': [str(username)],
                'objectClass': ['account', 'posixAccount', 'top', 'shadowAccount'],
                'userPassword': ['{crypt}%s' % password_sha512],
                'shadowLastChange': ['16328'],
                'shadowMin': ['0'],
                'shadowMax': ['99999'],
                'shadowWarning': ['7'],
                'loginShell': ['/bin/bash'],
                'uidNumber': [str(u.id)],
                'gidNumber': [str(u.id)],
                'homeDirectory': [str('/home/%s' % username)]}

            group_dn = "cn=%s,out=Group,%s" % (username, ldap_base_dn)
            group_attr = {
                'objectClass': ['posixGroup', 'top'],
                'cn': [str(username)],
                'userPassword': ['{crypt}x'],
                'gidNumber': [str(u.id)]
            }
            ldap_conn = LDAPMgmt()
            try:
                ldap_conn.add(user_dn, user_attr)
                ldap_conn.add(group_dn, group_attr)
            except Exception, e:
                error = u'添加ladp用户失败' + unicode(e)
                try:
                    bash('userdel -r %s' % username)
                    u.delete()
                    ldap_conn.delete(user_dn)
                    ldap_conn.delete(group_dn)
                except Exception:
                    pass
                return render_to_response('addUser.html', {'user_menu': 'active', 'form': form, 'error': error},
                                          context_instance=RequestContext(request))

            msg = u'添加用户成功'
    return render_to_response('addUser.html', {'user_menu': 'active', 'form': form, 'msg': msg},
                              context_instance=RequestContext(request))


@admin_required
def chgUser(request):
    """修改用户信息"""
    error = ''
    msg = ''
    jm = PyCrypt(key)

    if request.method == "GET":
        username = request.GET.get('username')
        if not username:
            return HttpResponseRedirect('/showUser/')
        user = User.objects.get(username=username)
        is_admin = "checked" if user.is_admin else ''
        is_superuser = 'checked' if user.is_superuser else ''
        groups = user.group.all()

        return render_to_response('chgUser.html',
                                  {'user': user, 'user_menu': 'active', 'is_admin': is_admin,
                                   'is_superuser': is_superuser, 'groups': groups},
                                  context_instance=RequestContext(request))
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_again = request.POST.get('password_again')
        key_pass = request.POST.get('key_pass')
        key_pass_again = request.POST.get('key_pass_again')
        name = request.POST.get('name')
        is_admin = request.POST.get('is_admin')
        is_superuser = request.POST.get('is_superuser')
        group_post = request.REQUEST.getlist('group')

        user = User.objects.get(username=username)
        is_admin = "checked" if user.is_admin else ''
        is_superuser = 'checked' if user.is_superuser else ''
        groups = user.group.all()

        keyfile = '%s/keys/%s' % (base_dir, username)

        # 如果用户是admin，那么不能委任其他admin或者超级用户
        if is_admin_user(request):
            is_admin = False
            is_superuser = False

        if password != password_again or key_pass != key_pass_again:
            error = u'密码不匹配'

        if '' in [username, password, key_pass, name, group_post]:
            error = u'带*内容不能为空'

        if len(password) < 6 or len(key_pass) < 6:
            error = u'密码长度需>6'

        u = User.objects.get(username=username)

        chg_keypass = bash('ssh-keygen -p -P %s -N %s -f %s' % (jm.decrypt(u.key_pass), key_pass, keyfile))

        if chg_keypass != 0:
            error = u'修改密钥密码失败'

        if error:
            return render_to_response('chgUser.html',
                                      {'user': user, 'user_menu': 'active', 'is_admin': is_admin,
                                       'is_superuser': is_superuser, 'groups': groups, 'error': error},
                                      context_instance=RequestContext(request))

        u.password = md5_crypt(password)
        u.key_pass = jm.encrypt(key_pass)
        u.name = name
        u.is_admin = is_admin
        u.is_superuser = is_superuser
        u.group = groups

        u.save()
        msg = u'修改用户信息成功'
        return render_to_response('chgUser.html',
                                  {'user': user, 'user_menu': 'active', 'is_admin': is_admin,
                                   'is_superuser': is_superuser, 'groups': groups, 'msg': msg},
                                  context_instance=RequestContext(request))


@admin_required
def showAssets(request):
    """查看服务器"""
    info = ''
    if request.session.get('admin') < 2:
        assets = []
        username = request.session.get('username')
        user = User.objects.get(username=username)
        for asset in user.assetsuser_set.all():
            assets.append(asset.aid)
    else:
        assets = Assets.objects.all()
    if request.method == 'POST':
        if request.session.get('admin') < 2:
            return HttpResponseRedirect('/showAssets/')
        assets_del = request.REQUEST.getlist('selected')
        for asset_id in assets_del:
            asset_del = Assets.objects.get(id=asset_id)
            asset_del.delete()
            info = '主机信息删除成功！'
    return render_to_response('showAssets.html', {'assets': assets, 'info': info, 'asset_menu': 'active'},
                              context_instance=RequestContext(request))


@superuser_required
def addAssets(request):
    """添加服务器"""
    error = ''
    msg = ''
    if request.method == 'POST':
        ip = request.POST.get('ip')
        port = request.POST.get('port')
        idc = request.POST.get('idc')
        comment = request.POST.get('comment')

        if '' in (ip, port):
            error = '带*号内容不能为空。'
        elif Assets.objects.filter(ip=ip):
            error = '主机已存在。'
        if not error:
            asset = Assets(ip=ip, port=port, idc=idc, comment=comment)
            asset.save()
            msg = u'%s 添加成功' % ip

    return render_to_response('addAssets.html', {'msg': msg, 'error': error, 'asset_menu': 'active'},
                              context_instance=RequestContext(request))


@admin_required
def showPerm(request):
    """查看权限"""
    if is_super_user(request):
        users = User.objects.all()
    else:
        users = group_member(request.session.get('username'))

    if request.method == 'POST':
        assets_del = request.REQUEST.getlist('selected')
        username = request.POST.get('username')
        user = User.objects.get(username=username)

        for asset_id in assets_del:
            asset = Assets.objects.get(id=asset_id)
            asset_user_del = AssetsUser.objects.get(uid=user, aid=asset)
            asset_user_del.delete()
        return HttpResponseRedirect('/showPerm/?username=%s' % username)

    elif request.method == 'GET':
        if request.GET.get('username'):
            username = request.GET.get('username')
            user = User.objects.filter(username=username)[0]
            assets_user = AssetsUser.objects.filter(uid=user.id)
            return render_to_response('perms.html',
                                      {'user': user, 'assets': assets_user, 'perm_menu': 'active'},
                                      context_instance=RequestContext(request))
    return render_to_response('showPerm.html', {'users': users, 'perm_menu': 'active'},
                              context_instance=RequestContext(request))


@admin_required
def addPerm(request):
    """增加授权"""
    if is_super_user(request):
        users = User.objects.all()
    else:
        users = group_member(request.session.get('username'))

    have_assets = []
    if request.method == 'POST':
        username = request.POST.get('username')
        assets_id = request.REQUEST.getlist('asset')
        user = User.objects.get(username=username)
        for asset_id in assets_id:
            asset = Assets.objects.get(id=asset_id)
            asset_user = AssetsUser(uid=user, aid=asset)
            asset_user.save()
        return HttpResponseRedirect('/addPerm/?username=%s' % username)

    elif request.method == 'GET':
        if request.GET.get('username'):
            username = request.GET.get('username')
            user = User.objects.get(username=username)
            assets_user = AssetsUser.objects.filter(uid=user.id)
            for asset_user in assets_user:
                have_assets.append(asset_user.aid)

            if request.session.get('admin') == 2:
                all_assets = Assets.objects.all()
            else:
                all_assets = user_assets(request.session.get('username'))
            other_assets = list(set(all_assets) - set(have_assets))
            return render_to_response('addUserPerm.html',
                                      {'user': user, 'assets': other_assets, 'perm_menu': 'active'},
                                      context_instance=RequestContext(request))

    return render_to_response('addPerm.html',
                              {'users': users, 'perm_menu': 'active'},
                              context_instance=RequestContext(request))





@login_required
def chgPass(request):
    """修改登录系统的密码"""
    error = ''
    msg = ''
    if request.method == 'POST':
        username = request.session.get('username')
        oldpass = request.POST.get('oldpass')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        user = User.objects.get(username)
        if '' in [oldpass, password, password_confirm]:
            error = '带*内容不能为空'
        elif md5_crypt(oldpass) != user.password:
            error = '密码不正确'
        elif password != password_confirm:
            error = '两次密码不匹配'

        if not error:
            user.password = md5_crypt(password)
            user.save()

    return render_to_response('chgPass.html', {'msg': msg, 'error': error, 'pass_menu': 'active'},
                              context_instance=RequestContext(request))


@login_required
def chgKey(request):
    """修改密钥密码"""
    error = ''
    msg = ''
    username = request.session.get('username')
    oldpass = request.POST.get('oldpass')
    password = request.POST.get('password')
    password_confirm = request.POST.get('password_confirm')
    keyfile = '%s/keys/%s' % (base_dir, username)

    if request.method == 'POST':
        if '' in [oldpass, password, password_confirm]:
            error = '带*内容不能为空'
        elif password != password_confirm:
            error = '两次密码不匹配'

        if not error:
            ret = subprocess.call('ssh-keygen -p -P %s -N %s -f %s' % (oldpass, password, keyfile), shell=True)
            if not ret:
                error = '原来密码不正确'
            else:
                msg = '修改密码成功'

    return render_to_response('chgKey.html',
                              {'error': error, 'msg': msg},
                              context_instance=RequestContext(request))

