# coding:utf-8
from __future__ import absolute_import, unicode_literals

import csv
import json
import uuid
import codecs
import chardet
from io import StringIO
from collections import defaultdict

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, reverse

from common.mixins import JSONResponseMixin
from common.utils import get_object_or_none
from .. import forms
from ..models import Asset, AssetGroup, AdminUser, IDC, SystemUser
from ..hands import AdminUserRequiredMixin
from ..tasks import update_assets_hardware_info


__all__ = ['AssetListView', 'AssetCreateView', 'AssetUpdateView',
           'UserAssetListView', 'AssetBulkUpdateView', 'AssetDetailView',
           'AssetModalListView', 'AssetDeleteView', 'AssetExportView',
           'BulkImportAssetView',
           ]


class AssetListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/asset_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'Asset list',
            'groups': AssetGroup.objects.all(),
            'system_users': SystemUser.objects.all(),
            # 'form': forms.AssetBulkUpdateForm(),
        }
        kwargs.update(context)
        return super(AssetListView, self).get_context_data(**kwargs)


class UserAssetListView(LoginRequiredMixin, TemplateView):
    template_name = 'assets/user_asset_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'Asset list',
            'system_users': SystemUser.objects.all(),
        }
        kwargs.update(context)
        return super(UserAssetListView, self).get_context_data(**kwargs)


class AssetCreateView(AdminUserRequiredMixin, CreateView):
    model = Asset
    form_class = forms.AssetCreateForm
    template_name = 'assets/asset_create.html'
    success_url = reverse_lazy('assets:asset-list')

    def form_valid(self, form):
        self.asset = asset = form.save()
        asset.created_by = self.request.user.username or 'Admin'
        asset.date_created = timezone.now()
        asset.save()
        return super(AssetCreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'Create asset',
        }
        kwargs.update(context)
        return super(AssetCreateView, self).get_context_data(**kwargs)

    def get_success_url(self):
        update_assets_hardware_info.delay([self.asset._to_secret_json()])
        return super(AssetCreateView, self).get_success_url()


class AssetModalListView(AdminUserRequiredMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = Asset
    context_object_name = 'asset_modal_list'
    template_name = 'assets/asset_modal_list.html'

    def get_context_data(self, **kwargs):
        assets = Asset.objects.all()
        assets_id = self.request.GET.get('assets_id', '')
        assets_id_list = [i for i in assets_id.split(',') if i.isdigit()]
        context = {
            'all_assets': assets_id_list,
            'assets': assets
        }
        kwargs.update(context)
        return super(AssetModalListView, self).get_context_data(**kwargs)


class AssetBulkUpdateView(AdminUserRequiredMixin, ListView):
    model = Asset
    form_class = forms.AssetBulkUpdateForm
    template_name = 'assets/asset_bulk_update.html'
    success_url = reverse_lazy('assets:asset-list')

    def get(self, request, *args, **kwargs):
        assets_id = self.request.GET.get('assets_id', '')
        self.assets_id_list = [int(i) for i in assets_id.split(',') if i.isdigit()]

        if kwargs.get('form'):
            self.form = kwargs['form']
        elif assets_id:
            self.form = self.form_class(
                initial={'assets': self.assets_id_list}
            )
        else:
            self.form = self.form_class()
        return super(AssetBulkUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            return redirect(self.success_url)
        else:
            return self.get(request, form=form, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # assets_list = Asset.objects.filter(id__in=self.assets_id_list)
        context = {
            'app': 'Assets',
            'action': 'Bulk update asset',
            'form': self.form,
            'assets_selected': self.assets_id_list,
            'assets': Asset.objects.all(),
        }
        kwargs.update(context)
        return super(AssetBulkUpdateView, self).get_context_data(**kwargs)


class AssetUpdateView(AdminUserRequiredMixin, UpdateView):
    model = Asset
    form_class = forms.AssetUpdateForm
    template_name = 'assets/asset_update.html'
    success_url = reverse_lazy('assets:asset-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'Update asset',
        }
        kwargs.update(context)
        return super(AssetUpdateView, self).get_context_data(**kwargs)

    def form_invalid(self, form):
        print(form.errors)
        return super(AssetUpdateView, self).form_invalid(form)


class AssetDeleteView(AdminUserRequiredMixin, DeleteView):
    model = Asset
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('assets:asset-list')


class AssetDetailView(DetailView):
    model = Asset
    context_object_name = 'asset'
    template_name = 'assets/asset_detail.html'

    def get_context_data(self, **kwargs):
        asset_groups = self.object.groups.all()
        system_users = self.object.system_users.all()
        context = {
            'app': 'Assets',
            'action': 'Asset detail',
            'asset_groups_remain': [asset_group for asset_group in AssetGroup.objects.all()
                                    if asset_group not in asset_groups],
            'asset_groups': asset_groups,
            'system_users_all': SystemUser.objects.all(),
            'system_users': system_users,
        }
        kwargs.update(context)
        return super(AssetDetailView, self).get_context_data(**kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class AssetExportView(View):
    def get(self, request):
        spm = request.GET.get('spm', '')
        assets_id_default = [Asset.objects.first().id] if Asset.objects.first() else [1]
        assets_id = cache.get(spm, assets_id_default)
        fields = [
            field for field in Asset._meta.fields
            if field.name not in [
                'date_created'
            ]
        ]
        filename = 'assets-{}.csv'.format(
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S'))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(codecs.BOM_UTF8)
        assets = Asset.objects.filter(id__in=assets_id)
        writer = csv.writer(response, dialect='excel',
                            quoting=csv.QUOTE_MINIMAL)

        header = [field.verbose_name for field in fields]
        header.append(_('Asset groups'))
        writer.writerow(header)

        for asset in assets:
            groups = ','.join([group.name for group in asset.groups.all()])
            data = [getattr(asset, field.name) for field in fields]
            data.append(groups)
            writer.writerow(data)
        return response

    def post(self, request, *args, **kwargs):
        try:
            assets_id = json.loads(request.body).get('assets_id', [])
        except ValueError:
            return HttpResponse('Json object not valid', status=400)
        spm = uuid.uuid4().hex
        cache.set(spm, assets_id, 300)
        url = reverse_lazy('assets:asset-export') + '?spm=%s' % spm
        return JsonResponse({'redirect': url})


class BulkImportAssetView(AdminUserRequiredMixin, JSONResponseMixin, FormView):
    form_class = forms.FileForm

    def form_valid(self, form):
        f = form.cleaned_data['file']
        det_result = chardet.detect(f.read())
        f.seek(0)  # reset file seek index
        file_data = f.read().decode(det_result['encoding']).strip(codecs.BOM_UTF8.decode())
        csv_file = StringIO(file_data)
        reader = csv.reader(csv_file)
        csv_data = [row for row in reader]
        fields = [
            field for field in Asset._meta.fields
            if field.name not in [
                'date_created'
            ]
        ]
        header_ = csv_data[0]
        mapping_reverse = {field.verbose_name: field.name for field in fields}
        mapping_reverse[_('Asset groups')] = 'groups'
        attr = [mapping_reverse.get(n, None) for n in header_]
        if None in attr:
            data = {'valid': False,
                    'msg': 'Must be same format as '
                           'template or export file'}
            return self.render_json_response(data)

        created, updated, failed = [], [], []
        assets = []
        for row in csv_data[1:]:
            if set(row) == {''}:
                continue

            asset_dict = dict(zip(attr, row))
            id_ = asset_dict.pop('id', 0)

            try:
                id_ = int(id_)
            except ValueError:
                id_ = 0

            asset = get_object_or_none(Asset, id=id_)
            for k, v in asset_dict.items():
                if k == 'idc':
                    v = get_object_or_none(IDC, name=v)
                elif k == 'is_active':
                    v = bool(v)
                elif k == 'admin_user':
                    v = get_object_or_none(AdminUser, name=v)
                elif k in ['port', 'cabinet_pos', 'cpu_count', 'cpu_cores']:
                    try:
                        v = int(v)
                    except ValueError:
                        v = 0
                elif k == 'groups':
                    groups_name = v.split(',')
                    v = AssetGroup.objects.filter(name__in=groups_name)
                else:
                    continue
                asset_dict[k] = v

            if not asset:
                try:
                    groups = asset_dict.pop('groups')
                    if len(Asset.objects.filter(hostname=asset_dict.get('hostname'))):
                        raise Exception(_('already exists'))
                    asset = Asset.objects.create(**asset_dict)
                    asset.groups.set(groups)
                    created.append(asset_dict['hostname'])
                    assets.append(asset)
                except Exception as e:
                    failed.append('%s: %s' % (asset_dict['hostname'], str(e)))
            else:
                for k, v in asset_dict.items():
                    if k == 'groups':
                        asset.groups.set(v)
                        continue
                    if v:
                        setattr(asset, k, v)
                try:
                    asset.save()
                    updated.append(asset_dict['hostname'])
                except Exception as e:
                    failed.append('%s: %s' % (asset_dict['hostname'], str(e)))

        if assets:
            update_assets_hardware_info.delay([asset._to_secret_json() for asset in assets])


        data = {
            'created': created,
            'created_info': 'Created {}'.format(len(created)),
            'updated': updated,
            'updated_info': 'Updated {}'.format(len(updated)),
            'failed': failed,
            'failed_info': 'Failed {}'.format(len(failed)),
            'valid': True,
            'msg': 'Created: {}. Updated: {}, Error: {}'.format(
                len(created), len(updated), len(failed))
        }
        return self.render_json_response(data)


