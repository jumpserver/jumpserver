#coding:utf-8
import django
import os
import sys
import random
import datetime

sys.path.append('../')
os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
#django.setup()


from juser.views import db_add_user, md5_crypt, CRYPTOR, db_add_group
from jasset.models import Asset, IDC, BisGroup
from juser.models import UserGroup, DEPT, User
from jperm.models import CmdGroup
from jlog.models import Log


def install():
    IDC.objects.create(name='ALL', comment='ALL')
    IDC.objects.create(name='默认', comment='默认')
    DEPT.objects.create(name="默认", comment="默认部门")
    DEPT.objects.create(name="超管部", comment="超级管理员部门")
    dept = DEPT.objects.get(name='超管部')
    dept2 = DEPT.objects.get(name='默认')
    UserGroup.objects.create(name='ALL', dept=dept, comment='ALL')
    UserGroup.objects.create(name='默认', dept=dept, comment='默认')

    BisGroup.objects.create(name='ALL', dept=dept, comment='ALL')
    BisGroup.objects.create(name='默认', dept=dept, comment='默认')

    User(id=5000, username="admin", password=md5_crypt('admin'),
         name='admin', email='admin@jumpserver.org', role='SU', is_active=True, dept=dept).save()
    User(id=5001, username="group_admin", password=md5_crypt('group_admin'),
         name='group_admin', email='group_admin@jumpserver.org', role='DA', is_active=True, dept=dept2).save()


def test_add_idc():
    for i in range(1, 20):
        name = 'IDC' + str(i)
        IDC.objects.create(name=name, comment='')
        print 'Add: %s' % name


def test_add_dept():
    for i in range(1, 100):
        name = 'DEPT' + str(i)
        print "Add: %s" % name
        DEPT.objects.create(name=name, comment=name)


def test_add_group():
    dept_all = DEPT.objects.all()
    for i in range(1, 100):
        name = 'UserGroup' + str(i)
        UserGroup.objects.create(name=name, dept=random.choice(dept_all), comment=name)
        print 'Add: %s' % name


def test_add_cmd_group():
    for i in range(1, 20):
        name = 'CMD' + str(i)
        cmd = '/sbin/ping%s, /sbin/ifconfig/' % str(i)
        CmdGroup.objects.create(name=name, cmd=cmd, comment=name)
        print 'Add: %s' % name


def test_add_user():
    for i in range(1, 500):
        username = "test" + str(i)
        dept_all = DEPT.objects.all()
        group_all = UserGroup.objects.all()
        group_all_id = [group.id for group in group_all]
        db_add_user(username=username,
                    password=md5_crypt(username),
                    dept=random.choice(dept_all),
                    name=username, email='%s@jumpserver.org' % username,
                    groups=[random.choice(group_all_id) for i in range(1, 4)], role='CU',
                    ssh_key_pwd=CRYPTOR.encrypt(username),
                    ldap_pwd=CRYPTOR.encrypt(username),
                    is_active=True,
                    date_joined=datetime.datetime.now())
        print "Add: %s" % username


def test_add_asset_group():
    dept = DEPT.objects.get(name='默认')
    for i in range(1, 20):
        name = 'AssetGroup' + str(i)
        group = BisGroup(name=name, dept=dept, comment=name)
        group.save()
        print 'Add: %s' % name


def test_add_asset():
    idc_all = IDC.objects.all()
    test_idc = random.choice(idc_all)
    bis_group_all = BisGroup.objects.all()
    dept_all = DEPT.objects.all()
    for i in range(1, 500):
        ip = '192.168.5.' + str(i)
        asset = Asset(ip=ip, port=22, login_type='L', idc=test_idc, is_active=True, comment='test')
        asset.save()
        asset.bis_group = [random.choice(bis_group_all) for i in range(2)]
        asset.dept = [random.choice(dept_all) for i in range(2)]
        print "Add: %s" % ip


def test_add_log():
    li_date = []
    today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    for i in range(0, 7):
        today = today-oneday
        li_date.append(today)
    user_list = ['马云', '马化腾', '丁磊', '周鸿祎', '雷军', '柳传志', '陈天桥', '李彦宏', '李开复', '罗永浩']
    for i in range(1, 1000):
        user = random.choice(user_list)
        ip = random.randint(1, 20)
        start_time = random.choice(li_date)
        end_time = datetime.datetime.now()
        log_path = '/var/log/jumpserver/test.log'
        host = '192.168.1.' + str(ip)
        Log.objects.create(user=user, host=host, remote_ip='8.8.8.8', dept_name='运维部', log_path=log_path, pid=168, start_time=start_time,
                           is_finished=1, log_finished=1, end_time=end_time)


if __name__ == '__main__':
    # install()
    # test_add_dept()
    # test_add_group()
    # test_add_user()
    # test_add_idc()
    # test_add_asset_group()
    test_add_asset()
    # test_add_log()




