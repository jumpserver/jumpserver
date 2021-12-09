# -*- coding: utf-8 -*-
#
from django.shortcuts import reverse, redirect


def redirect_to_guard_view(comment=''):
    continue_url = reverse('authentication:login-guard') + '?_=' + comment
    return redirect(continue_url)
