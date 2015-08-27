# coding: utf-8

from Crypto.PublicKey import RSA

from jumpserver.api import *


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
    """
    update a user info in database
    数据库更新用户信息
    """
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
    """
    delete a user from database
    从数据库中删除用户
    """
    try:
        user = User.objects.get(username=username)
        user.delete()
    except ObjectDoesNotExist:
        pass


def gen_ssh_key(username, password=None, length=2048):
    """
    generate a user ssh key in a property dir
    生成一个用户密钥
    """
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
    """
    add a system user in jumpserver
    在jumpserver服务器上添加一个用户
    """
    bash("useradd '%s'; echo '%s' | passwd --stdin '%s'" % (username, password, username))
    gen_ssh_key(username, ssh_key_pwd)


def server_del_user(username):
    """
    delete a user from jumpserver linux system
    删除系统上的某用户
    """
    bash('userdel -r %s' % username)


def ldap_add_user(username, ldap_pwd):
    """
    add a user in ldap database
    在LDAP中添加用户
    """
    user_dn = "uid=%s,ou=People,%s" % (username, LDAP_BASE_DN)
    password_sha512 = PyCrypt.gen_sha512(PyCrypt.gen_rand_pwd(6), ldap_pwd)
    user = User.objects.filter(username=username)
    if user:
        user = user[0]
    else:
        raise ServerError(u'用户 %s 不存在' % username)

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
    """
    delete a user in ldap database
    在ldap中删除某用户
    """
    user_dn = "uid=%s,ou=People,%s" % (username, LDAP_BASE_DN)
    group_dn = "cn=%s,ou=Group,%s" % (username, LDAP_BASE_DN)
    sudo_dn = 'cn=%s,ou=Sudoers,%s' % (username, LDAP_BASE_DN)

    ldap_conn.delete(user_dn)
    ldap_conn.delete(group_dn)
    ldap_conn.delete(sudo_dn)