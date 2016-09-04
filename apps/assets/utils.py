# ~*~ coding: utf-8 ~*~
#

from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy

from common.tasks import send_mail_async
from common.utils import reverse
from users.models import User


try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


class AdminUserRequiredMixin(UserPassesTestMixin):
    login_url = reverse_lazy('users:login')

    def test_func(self):
        return self.request.user.is_staff

