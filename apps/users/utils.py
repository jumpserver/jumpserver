# ~*~ coding: utf-8 ~*~
#

from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse_lazy


class AdminUserRequiredMixin(UserPassesTestMixin):
    login_url = reverse_lazy('users:login')

    def test_func(self):
        return self.request.user.is_staff
