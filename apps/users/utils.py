# ~*~ coding: utf-8 ~*~
#

from __future__ import unicode_literals
import os
import logging

from paramiko.rsakey import RSAKey
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy

from common.tasks import send_mail_async
from common.utils import reverse
from users.models import User


try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


logger = logging.getLogger('jumpserver')


class AdminUserRequiredMixin(UserPassesTestMixin):
    login_url = reverse_lazy('users:login')

    def test_func(self):
        return self.request.user.is_staff


def ssh_key_gen(length=2048, password=None, username='root', hostname=None):
    """Generate user ssh private and public key

    Use paramiko RSAKey generate it.

    """

    if hostname is None:
        hostname = os.uname()[1]

    f = StringIO.StringIO()

    try:
        logger.debug('Begin to generate ssh private key ...')
        private_key_obj = RSAKey.generate(length)
        private_key_obj.write_private_key(f, password=password)
        private_key = f.getvalue()

        public_key = "%(key_type)s %(key_content)s %(username)s@%(hostname)s" % {
            'key_type': private_key_obj.get_name(),
            'key_content': private_key_obj.get_base64(),
            'username': username,
            'hostname': hostname,
        }

        logger.debug('Finish to generate ssh private key ...')
        return private_key, public_key

    except IOError:
        raise IOError('These is error when generate ssh key.')


def user_add_success_next(user):
    subject = '您的用户创建成功'
    recipient_list = [user.email]
    message = """
    您好 %(name)s:
    </br>
    恭喜您，您的账号已经创建成功.
    </br>
    <a href="%(rest_password_url)s?token=%(rest_password_token)s">请点击这里设置密码</a>
    </br>
    这个链接有效期1小时, 超过时间您可以 <a href="%(forget_password_url)s?email=%(email)s">重新申请</a>

    </br>
    ---

    </br>
    <a href="%(login_url)s">直接登录</a>

    </br>
    """ % {
        'name': user.name,
        'rest_password_url': reverse('users:reset-password', external=True),
        'rest_password_token': User.generate_reset_token(user.email),
        'forget_password_url': reverse('users:forget-password', external=True),
        'email': user.email,
        'login_url': reverse('users:login', external=True),
    }

    send_mail_async.delay(subject, message, recipient_list, html_message=message)




