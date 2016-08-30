# ~*~ coding: utf-8 ~*~
#

import os
import logging

from paramiko.rsakey import RSAKey
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy

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





