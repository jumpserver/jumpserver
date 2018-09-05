添加组织及组织管理员说明
------------------------------------------------------
- jumpserver 1.4.0 或之后版本

::

    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py shell
    >>> from assets.models import Asset
    >>> from orgs.models import Organization
    >>> from users.models import User
    >>> dev_org = Organization.objects.create(name='开发部')
    >>> user = User.objects.create(name='用户', username='user', email='user@jumpserver.org')
    >>> user.set_password('PassWord')
    >>> user.save()
    >>> dev_org.admins.add(user)
    >>> exit()

    # 然后使用 user 用户登录 jumpserver 即可
