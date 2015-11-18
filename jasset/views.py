# coding:utf-8

import ast
from django.db.models import Q
from django.shortcuts import get_object_or_404
from jasset.asset_api import *
from jumpserver.api import *
from jasset.forms import AssetForm, IdcForm
from jasset.models import Asset, IDC, AssetGroup, ASSET_TYPE, ASSET_STATUS
from ansible_api import Tasks


@require_role('admin')
def group_add(request):
    """
    Add asset group
    添加资产组
    """
    header_title, path1, path2 = u'添加资产组', u'资产管理', u'添加资产组'
    asset_all = Asset.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '')
        asset_select = request.POST.getlist('asset_select', [])
        comment = request.POST.get('comment', '')

        try:
            if not name:
                error = u'组名不能为空'
                raise ServerError(error)

            asset_group_test = get_object(AssetGroup, name=name)
            if asset_group_test:
                error = u"该组名 %s 已存在" % name
                raise ServerError(error)

        except ServerError:
            pass

        else:
            db_add_group(name=name, comment=comment, asset_select=asset_select)
            smg = u"主机组 %s 添加成功" % name

    return my_render('jasset/group_add.html', locals(), request)


@require_role('admin')
def group_edit(request):
    """
    Edit asset group
    编辑资产组
    """
    header_title, path1, path2 = u'编辑主机组', u'资产管理', u'编辑主机组'
    group_id = request.GET.get('id', '')
    group = get_object(AssetGroup, id=group_id)

    asset_all = Asset.objects.all()
    asset_select = Asset.objects.filter(group=group)
    asset_no_select = [a for a in asset_all if a not in asset_select]

    if request.method == 'POST':
        name = request.POST.get('name', '')
        asset_select = request.POST.getlist('asset_select', [])
        comment = request.POST.get('comment', '')

        try:
            if not name:
                emg = u'组名不能为空'
                raise ServerError(emg)

            if group.name != name:
                asset_group_test = get_object(AssetGroup, name=name)
                if asset_group_test:
                    emg = u"该组名 %s 已存在" % name
                    raise ServerError(emg)

        except ServerError:
            pass

        else:
            group.asset_set.clear()
            db_update_group(id=group_id, name=name, comment=comment, asset_select=asset_select)
            smg = u"主机组 %s 添加成功" % name

        return HttpResponseRedirect('/jasset/group_list')

    return my_render('jasset/group_edit.html', locals(), request)


@require_role('admin')
def group_detail(request):
    """ 主机组详情 """
    header_title, path1, path2 = u'主机组详情', u'资产管理', u'主机组详情'
    group_id = request.GET.get('id', '')
    group = get_object(AssetGroup, id=group_id)
    asset_all = Asset.objects.filter(group=group).order_by('ip')

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(asset_all, request)
    return my_render('jasset/group_detail.html', locals(), request)


@require_role('admin')
def group_list(request):
    """
    list asset group
    列出资产组
    """
    header_title, path1, path2 = u'查看资产组', u'资产管理', u'查看资产组'
    keyword = request.GET.get('keyword', '')
    gid = request.GET.get('gid')
    sid = request.GET.get('sid')
    asset_group_list = AssetGroup.objects.all()

    if keyword:
        asset_group_list = asset_group_list.filter(Q(name__contains=keyword) | Q(comment__contains=keyword))

    asset_group_list, p, asset_groups, page_range, current_page, show_first, show_end = pages(asset_group_list, request)
    return my_render('jasset/group_list.html', locals(), request)


@require_role('admin')
def group_del(request):
    """
    del asset group
    删除主机组
    """
    group_ids = request.GET.get('id', '')
    group_id_list = group_ids.split(',')

    for group_id in group_id_list:
        AssetGroup.objects.filter(id=group_id).delete()

    return HttpResponse(u'删除成功')


@require_role('admin')
def asset_add(request):
    """
    Asset add view
    添加资产
    """
    header_title, path1, path2 = u'添加资产', u'资产管理', u'添加资产'
    asset_group_all = AssetGroup.objects.all()
    af = AssetForm()
    if request.method == 'POST':
        af_post = AssetForm(request.POST)
        print af_post
        ip = request.POST.get('ip', '')
        is_active = True if request.POST.get('is_active') == '1' else False
        use_default_auth = request.POST.get('use_default_auth', '')
        try:
            if Asset.objects.filter(ip=str(ip)):
                error = u'该IP %s 已存在!' % ip
                raise ServerError(error)

        except ServerError:
            pass
        else:
            if af_post.is_valid():
                asset_save = af_post.save(commit=False)
                if not use_default_auth:
                    password = request.POST.get('password', '')
                    password_encode = password
                    asset_save.password = password_encode
                asset_save.is_active = True if is_active else False
                asset_save.save()
                af_post.save_m2m()

                msg = u'主机 %s 添加成功' % ip
            else:
                esg = u'主机 %s 添加失败' % ip

    return my_render('jasset/asset_add.html', locals(), request)


@require_role('admin')
def asset_add_batch(request):
    header_title, path1, path2 = u'添加资产', u'资产管理', u'批量添加'
    return my_render('jasset/asset_add_batch.html', locals(), request)


@require_role('admin')
def asset_del(request):
    """
    del a asset
    删除主机
    """
    asset_id = request.GET.get('id', '')
    if asset_id:
        Asset.objects.filter(id=asset_id).delete()

    if request.method == 'POST':
        asset_batch = request.GET.get('arg', '')
        asset_id_all = str(request.POST.get('asset_id_all', ''))

        if asset_batch:
            for asset_id in asset_id_all.split(','):
                asset = get_object(Asset, id=asset_id)
                asset.delete()

    return HttpResponse(u'删除成功')


@require_role(role='super')
def asset_edit(request):
    """
    edit a asset
    修改主机
    """
    header_title, path1, path2 = u'修改资产', u'资产管理', u'修改资产'

    asset_id = request.GET.get('id', '')
    username = request.session.get('username', 'admin')
    asset = get_object(Asset, id=asset_id)
    asset_old = copy_model_instance(asset)
    af = AssetForm(instance=asset)
    if request.method == 'POST':
        af_post = AssetForm(request.POST, instance=asset)
        ip = request.POST.get('ip', '')
        use_default_auth = request.POST.get('use_default_auth')

        try:
            asset_test = get_object(Asset, ip=ip)
            if asset_test and asset_id != unicode(asset_test.id):
                error = u'该IP %s 已存在!' % ip
                raise ServerError(error)
        except ServerError:
            pass
        else:
            if af_post.is_valid():
                af_save = af_post.save(commit=False)
                if use_default_auth:
                    af_save.username = ''
                    af_save.password = ''
                af_save.save()
                af_post.save_m2m()
                # asset_new = get_object(Asset, id=asset_id)
                # asset_diff_one(asset_old, asset_new)
                info = asset_diff(af_post.__dict__.get('initial'), request.POST)
                db_asset_alert(asset, username, info)

                msg = u'主机 %s 修改成功' % ip
            else:
                emg = u'主机 %s 修改失败' % ip
            return HttpResponseRedirect('/jasset/asset_detail/?id=%s' % asset_id)

    return my_render('jasset/asset_edit.html', locals(), request)


@require_role('user')
def asset_list(request):
    """
    asset list view
    """
    idc_all = IDC.objects.filter()
    asset_group_all = AssetGroup.objects.all()
    asset_types = ASSET_TYPE
    asset_status = ASSET_STATUS

    idc_name = request.GET.get('idc', '')
    group_name = request.GET.get('group', '')
    asset_type = request.GET.get('asset_type', '')
    status = request.GET.get('status', '')
    keyword = request.GET.get('keyword', '')
    export = request.GET.get("export", False)

    asset_find = Asset.objects.all()
    if idc_name:
        asset_find = asset_find.filter(idc__name__contains=idc_name)

    if group_name:
        asset_find = asset_find.filter(group__name__contains=group_name)

    if asset_type:
        asset_find = asset_find.filter(asset_type__contains=asset_type)

    if status:
        asset_find = asset_find.filter(status__contains=status)

    if keyword:
        asset_find = asset_find.filter(
            Q(hostname__contains=keyword) |
            Q(other_ip__contains=keyword) |
            Q(ip__contains=keyword) |
            Q(remote_ip__contains=keyword) |
            Q(comment__contains=keyword) |
            Q(group__name__contains=keyword) |
            Q(cpu__contains=keyword) |
            Q(memory__contains=keyword) |
            Q(disk__contains=keyword))

    if export:
        s = write_excel(asset_find)
        if s[0]:
            file_name = s[1]
        smg = 'excel文件已生成，请点击下载!'
        return my_render('jasset/asset_excel_download.html', locals(), request)
    assets_list, p, assets, page_range, current_page, show_first, show_end = pages(asset_find, request)
    return my_render('jasset/asset_list.html', locals(), request)


@require_role('admin')
def asset_edit_batch(request):
    af = AssetForm()
    asset_group_all = AssetGroup.objects.all()
    return my_render('jasset/asset_edit_batch.html', locals(), request)


@require_role('admin')
def asset_detail(request):
    """
    Asset detail view
    """
    header_title, path1, path2 = u'主机详细信息', u'资产管理', u'主机详情'
    asset_id = request.GET.get('id', '')
    asset = get_object(Asset, id=asset_id)
    asset_record = AssetRecord.objects.filter(asset=asset).order_by('-alert_time')

    return my_render('jasset/asset_detail.html', locals(), request)


@require_role('admin')
def asset_update(request):
    """
    Asset update host info via ansible view
    """
    asset_id = request.GET.get('id', '')
    asset = get_object(Asset, id=asset_id)
    if not asset:
        return HttpResponseRedirect('/jasset/asset_detail/?id=%s' % asset_id)
    name = request.session.get('username', 'admin')
    if asset.use_default_auth:
        username = 'root'
        password = '123456'
    else:
        username = asset.username
        password = asset.password

    resource = [{"hostname": asset.ip, "port": asset.port,
                 "username": username, "password": password}]

    ansible_instance = Tasks(resource)
    ansible_asset_info = ansible_instance.get_host_info()
    if ansible_asset_info['status'] == 'ok':
        asset_info = ansible_asset_info['result'][asset.ip]
        if asset_info:
            hostname = asset_info.get('hostname')
            other_ip = ','.join(asset_info.get('other_ip'))
            cpu_type = asset_info.get('cpu_type')[1]
            cpu_cores = asset_info.get('cpu_cores')
            cpu = cpu_type + ' * ' + unicode(cpu_cores)
            memory = asset_info.get('memory')
            disk = asset_info.get('disk')
            sn = asset_info.get('sn')
            brand = asset_info.get('brand')
            system_type = asset_info.get('system_type')
            system_version = asset_info.get('system_version')

            asset_dic = {"hostname": hostname, "other_ip": other_ip, "cpu": cpu,
                         "memory": memory, "disk": disk, "system_type": system_type,
                         "system_version": system_version, "brand": brand, "sn": sn
                         }

            ansible_record(asset, asset_dic, name)

    return HttpResponseRedirect('/jasset/asset_detail/?id=%s' % asset_id)


@require_role('admin')
def idc_add(request):
    """
    IDC add view
    """
    header_title, path1, path2 = u'添加IDC', u'资产管理', u'添加IDC'
    if request.method == 'POST':
        idc_form = IdcForm(request.POST)
        if idc_form.is_valid():
            idc_name = idc_form.cleaned_data['name']

            if IDC.objects.filter(name=idc_name):
                emg = u'添加失败, 此IDC %s 已存在!' % idc_name
                return my_render('jasset/idc_add.html', locals(), request)
            else:
                idc_form.save()
                smg = u'IDC: %s添加成功' % idc_name
            return HttpResponseRedirect("/jasset/idc_list/")
    else:
        idc_form = IdcForm()
    return render_to_response('jasset/idc_add.html',
                              locals(),
                              context_instance=RequestContext(request))


@require_role('admin')
def idc_list(request):
    """
    IDC list view
    """
    header_title, path1, path2 = u'查看IDC', u'资产管理', u'查看IDC'
    posts = IDC.objects.all()
    keyword = request.GET.get('keyword', '')
    if keyword:
        posts = IDC.objects.filter(Q(name__contains=keyword) | Q(comment__contains=keyword))
    else:
        posts = IDC.objects.exclude(name='ALL').order_by('id')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)
    return render_to_response('jasset/idc_list.html',
                              locals(),
                              context_instance=RequestContext(request))


@require_role('admin')
def idc_edit(request):
    """
    IDC edit view
    """
    header_title, path1, path2 = u'编辑IDC', u'资产管理', u'编辑IDC'
    idc_id = request.GET.get('id', '')
    idc = get_object(IDC, id=idc_id)
    if request.method == 'POST':
        idc_form = IdcForm(request.POST, instance=idc)
        if idc_form.is_valid():
            idc_form.save()
            return HttpResponseRedirect("/jasset/idc_list/")
    else:
        idc_form = IdcForm(instance=idc)
        return my_render('jasset/idc_edit.html', locals(), request)


@require_role('admin')
def idc_detail(request):
    """
    IDC detail view
    """
    header_title, path1, path2 = u'IDC详情', u'资产管理', u'IDC详情'
    idc_id = request.GET.get('id', '')
    idc = get_object(IDC, id=idc_id)
    posts = Asset.objects.filter(idc=idc).order_by('ip')
    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    return my_render('jasset/idc_detail.html', locals(), request)


@require_role('admin')
def idc_del(request):
    """
    IDC delete view
    """
    uuid = request.GET.get('uuid', '')
    idc = get_object_or_404(IDC, uuid=uuid)
    idc.delete()
    return HttpResponseRedirect('/jasset/idc_list/')


@require_role('admin')
def asset_upload(request):
    """
    Upload file view
    """
    if request.method == 'POST':
        excel_file = request.FILES.get('file_name', '')
        ret = excel_to_db(excel_file)
        if ret:
            smg = u'批量添加成功'
        else:
            emg = u'批量添加失败,请检查格式.'
    return my_render('jasset/asset_add_batch.html', locals(), request)
