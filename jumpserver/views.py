#coding: utf-8

from django.http import HttpResponse
from django.shortcuts import render_to_response


def base(request):
    render_to_response('base.html')



