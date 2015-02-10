#coding:utf-8
import django
import os
import sys

sys.path.append('../')
os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
django.setup()

from juser.views import db_add_user, md5_crypt, CRYPTOR
from jasset.models import Asset, IDC
from jasset.views import jasset_group_add


def test_add_user():
    for i in range(1, 500):
        username = "test" + str(i)
        db_add_user(username=username,
                    password=md5_crypt(username),
                    name=username, email='%s@jumpserver.org' % username,
                    groups=[1,3], role='CU',
                    ssh_pwd=CRYPTOR.encrypt(username),
                    ssh_key_pwd=CRYPTOR.encrypt(username),
                    ldap_pwd=CRYPTOR.encrypt(username),
                    is_active=True,
                    date_joined=0)
        print "Add: %s" % username


def test_add_asset():
    test_idc = IDC.objects.get(id=1)
    for i in range(1, 500):
        ip = '192.168.1.' + str(i)
        Asset.objects.create(ip=ip, port=22, login_type='L', idc=test_idc, is_active=True, comment='test')
        print "Add: %s" % ip


if __name__ == '__main__':
    args = sys.argv
    if args[1] == 'user':
        test_add_user()
    if args[1] == 'asset':
        test_add_asset()




