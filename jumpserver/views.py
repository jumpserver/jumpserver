#coding: utf-8

from django.http import HttpResponse
from django.shortcuts import render_to_response


def base(request):
    return render_to_response('base1.html')
