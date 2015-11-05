# coding: utf-8

from Crypto.PublicKey import RSA

from juser.models import AdminGroup
from jumpserver.api import *
from  jumpserver.settings import BASE_DIR

def group_add_user(group, user_id=None, username=None):
    """
    用户组中添加用户
    UserGroup Add a user
    """
    if user_id:
        user = get_object(User, id=user_id)
    else:
        user = get_object(User, username=username)

    if user:
        group.user_set.add(user)


def db_add_group(**kwargs):
    """
    add a user group in database
    数据库中添加用户组
    """
    name = kwargs.get('name')
    group = get_object(UserGroup, name=name)
    users = kwargs.pop('users_id')

    if not group:
        group = UserGroup(**kwargs)
        group.save()
        for user_id in users:
            group_add_user(group, user_id)


def group_update_member(group_id, users_id_list):
    """
    user group update member
    用户组更新成员
    """
    group = get_object(UserGroup, id=group_id)
    if group:
        group.user_set.clear()
        for user_id in users_id_list:
            user = get_object(UserGroup, id=user_id)
            if isinstance(user, UserGroup):
                group.user_set.add(user)


def db_add_user(**kwargs):
    """
    add a user in database
    数据库中添加用户
    """
    groups_post = kwargs.pop('groups')
    admin_groups = kwargs.pop('admin_groups')
    role = kwargs.get('role', 'CU')
    user = User(**kwargs)
    user.set_password(kwargs.get('password'))
    user.save()
    if groups_post:
        group_select = []
        for group_id in groups_post:
            group = UserGroup.objects.filter(id=group_id)
            group_select.extend(group)
        user.group = group_select

    if admin_groups and role == 'GA':  # 如果是组管理员就要添加组管理员和组到管理组中
        for group_id in admin_groups:
            group = get_object(UserGroup, id=group_id)
            if group:
                AdminGroup(user=user, group=group).save()
    return user


def db_update_user(**kwargs):
    """
    update a user info in database
    数据库更新用户信息
    """
    groups_post = kwargs.pop('groups')
    admin_groups_post = kwargs.pop('admin_groups')
    user_id = kwargs.pop('user_id')
    user = User.objects.get(id=user_id)
    if user:
        pwd = kwargs.pop('password')
        user.update(**kwargs)
        if pwd != '':
            user.set_password(pwd)
        user.save()
    else:
        return None

    group_select = []
    if groups_post:
        for group_id in groups_post:
            group = UserGroup.objects.filter(id=group_id)
            group_select.extend(group)
    user.group = group_select

    if admin_groups_post != '':
        user.admingroup_set.all().delete()
        for group_id in admin_groups_post:
            group = get_object(UserGroup, id=group_id)
            AdminGroup(user=user, group=group).save()


def db_del_user(username):
    """
    delete a user from database
    从数据库中删除用户
    """
    user = get_object(User, username=username)
    if user:
        user.delete()


def gen_ssh_key(username, password=None, length=2048):
    """
    generate a user ssh key in a property dir
    生成一个用户ssh密钥对
    """
    print "gen_ssh_key" + str(time.time())
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
    print "gen_ssh_pub_key" + str(time.time())
    pub_key = key.publickey()
    with open(public_key_file, 'w') as pub_f:
        pub_f.write(pub_key.exportKey('OpenSSH'))
    os.chmod(public_key_file, 0600)
    bash('chown %s:%s %s' % (username, username, public_key_file))
    print "gen_ssh_key_end" + str(time.time())


def server_add_user(username, password, ssh_key_pwd, ssh_key_login_need):
    """
    add a system user in jumpserver
    在jumpserver服务器上添加一个用户
    """
    bash("useradd '%s'; echo '%s'; echo '%s' | passwd --stdin '%s'" % (username, password, password, username))
    if ssh_key_login_need:
        gen_ssh_key(username, ssh_key_pwd)


def user_add_mail(user, kwargs):
    """
    add user send mail
    发送用户添加邮件
    """
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    mail_title = u'恭喜你的跳板机用户 %s 添加成功 Jumpserver' % user.name
    mail_msg = u"""
    Hi, %s
        您的用户名： %s
        您的角色： %s
        您的web登录密码： %s
        您的ssh密钥文件密码： %s
        密钥下载地址： %s/juser/down_key/?uuid=%s
        说明： 请登陆后再下载密钥！
    """ % (user.name, user.username, user_role.get(user.role, u'普通用户'),
           kwargs.get('password'), kwargs.get('ssh_key_pwd'), URL, user.uuid)
    send_mail(mail_title, mail_msg, MAIL_FROM, [user.email], fail_silently=False)


def server_del_user(username):
    """
    delete a user from jumpserver linux system
    删除系统上的某用户
    """
    bash('userdel -r %s' % username)


def get_display_msg(user, password, ssh_key_pwd, ssh_key_login_need, send_mail_need):
    if send_mail_need:
        msg = u'添加用户 %s 成功！ 用户密码已发送到 %s 邮箱！' % (user.name, user.email)
        return msg

    if ssh_key_login_need:
        msg = u"""
        跳板机地址： %s
        用户名：%s
        密码：%s
        密钥密码：%s
        密钥下载url: %s/juser/down_key/?id=%s
        该账号密码可以登陆web和跳板机。
        """ % (URL, user.username, password, ssh_key_pwd, URL, user.id)
    else:
        msg = u"""
        跳板机地址： %s \n
        用户名：%s \n
        密码：%s \n
        该账号密码可以登陆web和跳板机。
        """ % (URL, user.username, password)

    return msg

# def ldap_add_user(username, ldap_pwd):
#     """
#     add a user in ldap database
#     在LDAP中添加用户
#     """
#     user_dn = "uid=%s,ou=People,%s" % (username, LDAP_BASE_DN)
#     password_sha512 = PyCrypt.gen_sha512(PyCrypt.random_pass(6), ldap_pwd)
#     user = get_object(User, username=username)
#     if not user:
#         raise ServerError(u'用户 %s 不存在' % username)
#
#     user_attr = {'uid': [str(username)],
#                  'cn': [str(username)],
#                  'objectClass': ['account', 'posixAccount', 'top', 'shadowAccount'],
#                  'userPassword': ['{crypt}%s' % password_sha512],
#                  'shadowLastChange': ['16328'],
#                  'shadowMin': ['0'],
#                  'shadowMax': ['99999'],
#                  'shadowWarning': ['7'],
#                  'loginShell': ['/bin/bash'],
#                  'uidNumber': [str(user.id)],
#                  'gidNumber': [str(user.id)],
#                  'homeDirectory': [str('/home/%s' % username)]}
#
#     group_dn = "cn=%s,ou=Group,%s" % (username, LDAP_BASE_DN)
#     group_attr = {'objectClass': ['posixGroup', 'top'],
#                   'cn': [str(username)],
#                   'userPassword': ['{crypt}x'],
#                   'gidNumber': [str(user.id)]}
#
#     ldap_conn.add(user_dn, user_attr)
#     ldap_conn.add(group_dn, group_attr)


# def ldap_del_user(username):
#     """
#     delete a user in ldap database
#     在ldap中删除某用户
#     """
#     user_dn = "uid=%s,ou=People,%s" % (username, LDAP_BASE_DN)
#     group_dn = "cn=%s,ou=Group,%s" % (username, LDAP_BASE_DN)
#     sudo_dn = 'cn=%s,ou=Sudoers,%s' % (username, LDAP_BASE_DN)
#
#     ldap_conn.delete(user_dn)
#     ldap_conn.delete(group_dn)
#     ldap_conn.delete(sudo_dn)