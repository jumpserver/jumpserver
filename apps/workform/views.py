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

import pymongo

def test1(request):
    aaa = 'sdfsaf'
    return render(request, 'workform/test1.html')

def service_msg(request):
    if request.method == "POST":
        phone_number = str(request.POST.get("phoneno")).strip()        # 1: 要查询的手机号码

        # 一：查询医药实名认证信息(查询RealNameAuthentication库,获取医药实名认证信息)
        conn = pymongo.MongoClient('103.244.234.57', port=27017, )
        dbRealNameAuthentication = conn.RealNameAuthentication
        RealName = dbRealNameAuthentication.UserIdentity.find({"IdentityId": phone_number})
        RealNameList = []
        for i in RealName:
            if i['AccountId']['AccountType'] == 'MedPerson':
                # v = {'ObjectId': str(i['_id']), 'AccountType': i['AccountId']['AccountType'], 'Key': i['AccountId']['Key'], 'IdentityType': i['IdentityType'], 'IdentityId': i['IdentityId']}
                v = {'ObjectId': str(i['_id']), 'AccountType': '医学网平台', 'Key': i['AccountId']['Key'], 'IdentityType': i['IdentityType'], 'IdentityId': i['IdentityId']}
                RealNameList.append(v)
        print(RealNameList)
        return render(request, 'workform/service_msg.html', locals())
    return render(request, 'workform/service_msg.html')