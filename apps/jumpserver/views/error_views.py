# -*- coding: utf-8 -*-
#
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.translation import gettext

__all__ = ['handler404', 'handler500']


def handler404(request, *args, **argv):
    if request.content_type.find('application/json') > -1:
        response = JsonResponse({'error': gettext('Not found')}, status=404)
    else:
        response = render(request, '404.html', status=404)
    return response


def handler500(request, *args, **argv):
    if request.get_preferred_type(['text/html', 'application/json']) == 'application/json':
        response = JsonResponse({'error': gettext('Server internal error')}, status=500)
    else:
        response = render(request, '500.html', status=500)
    return response
