# coding: utf-8

import hashlib
from ConfigParser import ConfigParser
import os
import datetime
import json

from django.db.models import Count
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.template import RequestContext

from juser.models import User, UserGroup
from jlog.models import Log
from jasset.models import Asset, BisGroup, IDC
from jumpserver.api import *


def getDaysByNum(num):
    today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    li_date, li_str = [], []
    for i in range(0, num):
        today = today-oneday
        li_date.append(today)
        li_str.append(str(today)[5:10])
    li_date.reverse()
    li_str.reverse()
    t = (li_date, li_str)
    return t


def get_data(data, items, option):
    dic = {}
    li_date, li_str = getDaysByNum(7)
    for item in items:
        li = []
        name = item[option]
        if option == 'user':
            option_data = data.filter(user=name)
        elif option == 'host':
            option_data = data.filter(host=name)
        for t in li_date:
            year, month, day = t.year, t.month, t.day
            times = option_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).count()
            li.append(times)
        dic[name] = li
    return dic


@require_login
def index(request):
    path1, path2 = u'仪表盘', 'Dashboard'
    users = User.objects.all()
    hosts = Asset.objects.all()
    online_host = Log.objects.filter(is_finished=0)
    online_user = online_host.distinct()
    li_date, li_str = getDaysByNum(7)
    today = datetime.datetime.now().day
    from_week = datetime.datetime.now() - datetime.timedelta(days=7)
    week_data = Log.objects.filter(start_time__range=[from_week, datetime.datetime.now()])
    user_top_ten = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:10]
    host_top_ten = week_data.values('host').annotate(times=Count('host')).order_by('-times')[:10]
    user_dic, host_dic = get_data(week_data, user_top_ten, 'user'), get_data(week_data, host_top_ten, 'host')
    print "##############%s" % request.session.get('role_id')

    top = {'user': '活跃用户数', 'host': '活跃主机数', 'times': '登录次数'}
    top_dic = {}
    for key, value in top.items():
        li = []
        for t in li_date:
            year, month, day = t.year, t.month, t.day
            if key != 'times':
                times = week_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).values(key).distinct().count()
            else:
                times = week_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).count()
            li.append(times)
        top_dic[value] = li
    return render_to_response('index.html', locals(), context_instance=RequestContext(request))


def skin_config(request):
    return render_to_response('skin_config.html')


def jasset_group_add(name, comment, jtype):
    if BisGroup.objects.filter(name=name):
        emg = u'该业务组已存在!'
    else:
        BisGroup.objects.create(name=name, comment=comment, type=jtype)
        smg = u'业务组%s添加成功' % name


def page_list_return(total, current=1):
    min_page = current - 2 if current - 4 > 0 else 1
    max_page = min_page + 4 if min_page + 4 < total else total

    return range(min_page, max_page+1)


def jasset_host_edit(j_id, j_ip, j_idc, j_port, j_type, j_group, j_active, j_comment, j_user='', j_password=''):
    groups = []
    is_active = {u'是': '1', u'否': '2'}
    login_types = {'LDAP': 'L', 'SSH_KEY': 'S', 'PASSWORD': 'P', 'MAP': 'M'}
    for group in j_group[0].split():
        c = BisGroup.objects.get(name=group.strip())
        groups.append(c)
    j_type = login_types[j_type]
    j_idc = IDC.objects.get(name=j_idc)
    a = Asset.objects.get(id=j_id)
    if j_type == 'M':
        a.ip = j_ip
        a.port = j_port
        a.login_type = j_type
        a.idc = j_idc
        a.is_active = j_active
        a.comment = j_comment
        a.username = j_user
        a.password = j_password
    else:
        a.ip = j_ip
        a.port = j_port
        a.idc = j_idc
        a.login_type = j_type
        a.is_active = is_active[j_active]
        a.comment = j_comment
    a.save()
    a.bis_group = groups
    a.save()


def pages(posts, r):
    """分页公用函数"""
    contact_list = posts
    p = paginator = Paginator(contact_list, 10)
    try:
        current_page = int(r.GET.get('page', '1'))
    except ValueError:
        current_page = 1

    page_range = page_list_return(len(p.page_range), current_page)

    try:
        contacts = paginator.page(current_page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)

    if current_page >= 5:
        show_first = 1
    else:
        show_first = 0
    if current_page <= (len(p.page_range) - 3):
        show_end = 1
    else:
        show_end = 0

    return contact_list, p, contacts, page_range, current_page, show_first, show_end


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
                request.session['user_id'] = user.id
                if user.role == 'SU':
                    request.session['role_id'] = 2
                elif user.role == 'DA':
                    request.session['role_id'] = 1
                else:
                    request.session['role_id'] = 0
                return HttpResponseRedirect('/')
            else:
                error = '密码错误，请重新输入。'
        else:
            error = '用户不存在。'
    return render_to_response('login.html', {'error': error})


def logout(request):
    request.session.delete()
    return HttpResponseRedirect('/login/')


def filter_ajax_api(request):
    attr = request.GET.get('attr', 'user')
    value = request.GET.get('value', '')
    if attr == 'user':
        contact_list = User.objects.filter(name__icontains=value)
    elif attr == "user_group":
        contact_list = UserGroup.objects.filter(name__icontains=value)
    elif attr == "asset":
        contact_list = Asset.objects.filter(ip__icontains=value)
    elif attr == "asset":
        contact_list = BisGroup.objects.filter(name__icontains=value)

    return render_to_response('filter_ajax_api.html', locals())


# def perm_user_asset(user_id=None, username=None):
#     if user_id:
#         user = User.objects.get(id=user_id)
#     else:
#         user = User.objects.get(username=username)
#     user_groups = user.user_group.all()
#     perms = []
#     assets = []
#     asset_groups = []
#     for user_group in user_groups:
#         perm = user_group.perm_set.all()
#         perms.extend(perm)
#
#     for perm in perms:
#         asset_groups.extend(perm.asset_group.all())
#
#     for asset_group in asset_groups:
#         assets.extend(list(asset_group.asset_set.all()))
#
#     return assets


def install(request):
    from juser.models import DEPT, User
    dept = DEPT(id=1, name="超管部", comment="超级管理员部门")
    dept.save()
    dept2 = DEPT(id=2, name="默认", comment="默认部门")
    dept2.save()
    User(id=5000, username="admin", password=md5_crypt('admin'),
         name='admin', email='admin@jumpserver.org', role='SU', is_active=True, dept=dept).save()
    User(id=5001, username="group_admin", password=md5_crypt('group_admin'),
         name='group_admin', email='group_admin@jumpserver.org', role='DA', is_active=True, dept=dept2).save()
    return HttpResponse('Ok')

