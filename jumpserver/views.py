#coding: utf-8

from django.http import HttpResponse
from django.shortcuts import render_to_response


def base(request):
    return render_to_response('base.html')


def skin_config(request):
    return render_to_response('skin_config.html')


def header_path(header_title, path1, path2):
    return header_title, path1, path2
