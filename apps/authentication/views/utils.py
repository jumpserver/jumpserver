# -*- coding: utf-8 -*-
#
from django.shortcuts import reverse, redirect


def redirect_to_guard_view():
    continue_url = reverse('authentication:login-guard')
    return redirect(continue_url)
