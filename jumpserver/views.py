#coding: utf-8

import hashlib

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect

from juser.models import User


def md5_crypt(string):
    return hashlib.new("md5", string).hexdigest()


def base(request):
    return render_to_response('base.html')


def skin_config(request):
    return render_to_response('skin_config.html')


def login(request):
    """登录界面"""
    if request.session.get('username'):
        return HttpResponseRedirect('/')
    if request.method == 'GET':
        return render_to_response('login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = User.objects.filter(username=username)
        if user:
            user = user[0]
            if md5_crypt(password) == user.password:
                request.session['username'] = username
                if user.role == 'SU':
                    request.session['role'] = 2
                elif user.role == 'GA':
                    request.session['role'] = 1
                else:
                    request.session['role'] = 0
                return HttpResponseRedirect('/')
            else:
                error = '密码错误，请重新输入。'
        else:
            error = '用户不存在。'
    return render_to_response('login.html', {'error': error})


def logout(request):
    request.session.delete()
    return HttpResponseRedirect('/login/')


