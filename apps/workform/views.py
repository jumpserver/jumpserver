'''
这是work_form的视图配置文件
'''

from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

# Create your views here.
from .models import *
from . import models
from datetime import datetime

def test1(request):
    aaa = 'sdfsaf'
    return render(request, 'workform/test1.html')