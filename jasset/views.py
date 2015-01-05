#coding:utf-8
from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect


def index(request):
    return render_to_response('jasset/jasset.html',)


def jadd(request):
    if request.method == 'POST':
        pass
    return render_to_response('jasset/jadd.html',)