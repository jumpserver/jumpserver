#coding: utf-8
import os
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
django.setup()
from juser.models import User, Group
from jasset.models import Asset, IDC
from jpermission.models import Permission


g = Group(name='wzp', comment='wzp project')
g.save()

u = User(username='hadoop', password='hadoop', name='hadoop', email='ibuler@qq.com', group=g,
         ldap_pwd='hadoop', ssh_key_pwd='hadoop', date_joined=0)
u.save()

i = IDC(name='lf')
i.save()

a = Asset(ip='172.16.1.122', port=2001, idc=i, group=g, date_added=0)
a.save()

p = Permission(user=u, asset=a)
p.save()



