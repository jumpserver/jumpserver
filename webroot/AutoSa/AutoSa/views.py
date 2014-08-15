#coding: utf-8

from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from UserManage.models import User
from Assets.models import Assets, AssetsUser
import subprocess
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import random
import ConfigParser
import pam


base_dir = "/opt/jumpserver/"
cf = ConfigParser.ConfigParser()
cf.read('%s/jumpserver.conf' % base_dir)

key = cf.get('jumpserver', 'key')
useradd_shell = cf.get('jumpserver', 'useradd_shell')
userdel_shell = cf.get('jumpserver', 'userdel_shell')
sudoadd_shell = cf.get('jumpserver', 'sudoadd_shell')
sudodel_shell = cf.get('jumpserver', 'sudodel_shell')
keygen_shell = cf.get('jumpserver', 'keygen_shell')
chgpass_shell = cf.get('jumpserver', 'chgpass_shell')
admin = ['admin']


def keygen(num):
    """生成随机密码"""
    seed = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    sa = []
    for i in range(num):
        sa.append(random.choice(seed))
    salt = ''.join(sa)
    return salt


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


def login(request):
    """登录界面"""
    if request.session.get('username'):
        return HttpResponseRedirect('/')
    if request.method == 'GET':
        return render_to_response('login.html')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if pam.authenticate(username, password):
            if username in admin:
                request.session['username'] = username
                request.session['admin'] = 1
            else:
                request.session['username'] = username
                request.session['admin'] = 0
            return HttpResponseRedirect('/')
        else:
            error = '密码错误，请重新输入。'

        return render_to_response('login.html',{'error': error})


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


def logout(request):
    """注销登录调用"""
    if request.session.get('username'):
        del request.session['username']
    return HttpResponseRedirect('/login/')


@login_required
def downKey(request):
    """下载key"""
    username = request.session.get('username')
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
    users = User.objects.all()
    info = ''
    error = ''
    if request.method == 'POST':
        selected_user = request.REQUEST.getlist('selected')
        if selected_user:
            for id in selected_user:
                user_del = User.objects.get(id=id)
                username = user_del.username
                subprocess.call("'%s' '%s';'%s' '%s';" %
                                (userdel_shell, username, sudodel_shell, username), shell=True)
                user_del.delete()
                info = "删除用户成功。"
    return render_to_response('showUser.html',
                              {'users': users, 'info': info, 'error': error, 'user_menu': 'active'},
                              context_instance=RequestContext(request))


@admin_required
def addUser(request):
    """添加用户"""
    jm = PyCrypt(key)
    if request.method == 'GET':
        return render_to_response('addUser.html', {'user_menu': 'active'},
                                  context_instance=RequestContext(request))
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        keypass = request.POST.get('keypass')
        keypass_confirm = request.POST.get('keypass_confirm')
        name = request.POST.get('name')
        email = request.POST.get('email')
        error = ''

        if '' in (username, password, password_confirm, name):
            error += '带*号内容不能为空。'
        if User.objects.filter(username=username):
            error += '用户名已存在。'
        if password != password_confirm or keypass != keypass_confirm:
            error += '两次输入密码不匹配。'
        if error:
            return render_to_response('addUser.html', {'error': error, 'user_menu': 'active'},
                                      context_instance=RequestContext(request))
        ldap_password = keygen(15)
        ret = subprocess.call("%s '%s' '%s';%s '%s';%s '%s' '%s'" %
                              (useradd_shell, username, ldap_password,
                               sudoadd_shell, username,
                               keygen_shell, username, keypass), shell=True)

        if not ret:
            ret = subprocess.call('echo %s | passwd --stdin %s' % (password, username), shell=True)
            if not ret:
                user = User(username=username,
                            password=jm.encrypt(ldap_password),
                            name=name,
                            email=email)
                user.save()
                msg = u'添加用户 %s 成功。' % name
            else:
                msg = u'添加用户 %s 失败。' % name
        else:
            msg = u'添加用户 %s 失败。' % name

        return render_to_response('addUser.html', {'msg': msg, 'user_menu': 'active'},
                                  context_instance=RequestContext(request))


@admin_required
def showAssets(request):
    """查看服务器"""
    info = ''
    assets = Assets.objects.all()
    if request.method == 'POST':
        assets_del = request.REQUEST.getlist('selected')
        for asset_id in assets_del:
            asset_del = Assets.objects.get(id=asset_id)
            asset_del.delete()
            info = '主机信息删除成功！'
    return render_to_response('showAssets.html', {'assets': assets, 'info': info, 'asset_menu': 'active'},
                              context_instance=RequestContext(request))


@admin_required
def addAssets(request):
    """添加服务器"""
    error = ''
    msg = ''
    if request.method == 'POST':
        ip = request.POST.get('ip')
        port = request.POST.get('port')
        comment = request.POST.get('comment')

        if '' in (ip, port):
            error = '带*号内容不能为空。'
        elif Assets.objects.filter(ip=ip):
            error = '主机已存在。'
        if not error:
            asset = Assets(ip=ip, port=port, comment=comment)
            asset.save()
            msg = u'%s 添加成功' % ip

    return render_to_response('addAssets.html', {'msg': msg, 'error': error, 'asset_menu': 'active'},
                              context_instance=RequestContext(request))


@admin_required
def showPerm(request):
    """查看权限"""
    users = User.objects.all()
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
    users = User.objects.all()
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
            all_assets = Assets.objects.all()
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
        if '' in [oldpass, password, password_confirm]:
            error = '带*内容不能为空'
        elif not pam.authenticate(username, oldpass):
            error = '密码不正确'
        elif password != password_confirm:
            error = '两次密码不匹配'

        if not error:
            ret = subprocess.call('%s %s %s' % (chgpass_shell, username, password), shell=True)
            if ret:
                error = '密码修改失败'
            else:
                msg = '修改密码成功'

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

