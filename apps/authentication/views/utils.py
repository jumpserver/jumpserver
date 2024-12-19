# -*- coding: utf-8 -*-
#
from urllib.parse import urlencode, parse_qsl

from django.shortcuts import reverse, redirect


def redirect_to_guard_view(comment='', query_string=None):
    params = {'_': comment}
    base_url = reverse('authentication:login-guard')

    if query_string:
        params.update(dict(parse_qsl(query_string)))

    query_string = urlencode(params)

    continue_url = f"{base_url}?{query_string}"
    return redirect(continue_url)
