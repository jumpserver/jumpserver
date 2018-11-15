添加组织及组织管理员说明
------------------------------------------------------
- jumpserver 1.4.0 或之后版本

.. code-block:: shell

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
    >>> dev_org.users.add(user)
    >>> exit()

    # 然后使用 user 用户登录 jumpserver 即可


向现有组织加入管理员

.. code-block:: shell

    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py shell
    >>> from assets.models import Asset
    >>> from orgs.models import Organization
    >>> from users.models import User
    >>> dev_org = Organization.objects.get(name='开发部')
    >>> user = User.objects.get(username='admin')
    >>> dev_org.admins.add(user)
    >>> exit()


向现有组织加入已存在用户

.. code-block:: shell

    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py shell
    >>> from assets.models import Asset
    >>> from orgs.models import Organization
    >>> from users.models import User
    >>> dev_org = Organization.objects.get(name='开发部')
    >>> user = User.objects.get(username='admin')
    >>> dev_org.users.add(user)
    >>> exit()


向现有组织加入新建的用户

.. code-block:: shell

    $ source /opt/py3/bin/activate
    $ cd /opt/jumpserver/apps
    $ python manage.py shell
    >>> from assets.models import Asset
    >>> from orgs.models import Organization
    >>> from users.models import User
    >>> dev_org = Organization.objects.get(name='开发部')
    >>> user = User.objects.create(name='测试用户', username='test', email='test@jumpserver.org')
    >>> user.set_password('PassWord')
    >>> user.save()
    >>> dev_org.users.add(user)
    >>> exit()
