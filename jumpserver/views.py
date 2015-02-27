#coding: utf-8

import hashlib
import datetime
import json

from django.db.models import Count
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, InvalidPage

from juser.models import User
from jlog.models import Log
from jasset.models import Asset, BisGroup, IDC


def md5_crypt(string):
    return hashlib.new("md5", string).hexdigest()


def getDaysByNum(num):
    today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    li_date, li_str = [], []
    for i in range(0, num):
        today = today-oneday
        li_date.append(today)
        li_str.append(str(today)[0:10])
    li_date.reverse()
    li_str.reverse()
    t = (li_date, li_str)
    return t


def index(request):
    path1, path2 = u'仪表盘', 'Dashboard'
    dic = {}
    li_date, li_str = getDaysByNum(7)
    # li_str = json.dumps(li_str)
    # print li_str, type(li_str)
    today = datetime.datetime.now().day
    from_week = datetime.datetime.now() - datetime.timedelta(days=7)
    week_data = Log.objects.filter(start_time__range=[from_week, datetime.datetime.now()])
    top_ten = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:10]
    for user in top_ten:
        username = user['user']
        li = []
        user_data = week_data.filter(user=username)
        for t in li_date:
            year, month, day = t.year, t.month, t.day
            times = user_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).count()
            li.append(times)
        dic[username] = li
    print dic
    users = User.objects.all()
    hosts = Asset.objects.all()
    online_host = Log.objects.filter(is_finished=0)
    online_user = online_host.distinct()
    return render_to_response('index.html', locals())


def skin_config(request):
    return render_to_response('skin_config.html')


def jasset_group_add(name, comment, jtype):
    if BisGroup.objects.filter(name=name):
        emg = u'该业务组已存在!'
    else:
        BisGroup.objects.create(name=name, comment=comment, type=jtype)
        smg = u'业务组%s添加成功' %name


def jasset_host_edit(j_id, j_ip, j_idc, j_port, j_type, j_group, j_active, j_comment):
    groups = []
    is_active = {u'是': '1', u'否': '2'}
    login_types = {'LDAP': 'L', 'SSH_KEY': 'S', 'PASSWORD': 'P', 'MAP': 'M'}
    for group in j_group[0].split():
        print group.strip()
        c = BisGroup.objects.get(name=group.strip())
        groups.append(c)
    j_type = login_types[j_type]
    print j_type
    j_idc = IDC.objects.get(name=j_idc)
    print j_idc
    print
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
    contact_list = posts
    p = paginator = Paginator(contact_list, 10)
    try:
        page = int(r.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        contacts = paginator.page(page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)

    return contact_list, p, contacts


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

