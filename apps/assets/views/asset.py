# coding:utf-8
from __future__ import absolute_import, unicode_literals

import csv
import json
import uuid
import codecs
from io import StringIO

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
from django.shortcuts import get_object_or_404, redirect

from common.mixins import JSONResponseMixin
from common.utils import get_object_or_none
from .. import forms
from ..models import Asset, AssetGroup, AdminUser, IDC, SystemUser
from ..hands import AdminUserRequiredMixin
from ..tasks import update_assets_hardware_info


__all__ = ['AssetListView', 'AssetCreateView', 'AssetUpdateView',
           'UserAssetListView', 'AssetModalCreateView', 'AssetDetailView',
           'AssetModalListView', 'AssetDeleteView', 'AssetExportView',
           'BulkImportAssetView',
           ]


class AssetListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/asset_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'asset list',
            'groups': AssetGroup.objects.all(),
            'system_users': SystemUser.objects.all(),
        }
        kwargs.update(context)
        return super(AssetListView, self).get_context_data(**kwargs)


class UserAssetListView(LoginRequiredMixin, TemplateView):
    template_name = 'assets/user_asset_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'asset list',
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


class AssetModalCreateView(AdminUserRequiredMixin, ListView):
    model = Asset
    form_class = forms.AssetCreateForm
    template_name = 'assets/asset_modal_update.html'
    success_url = reverse_lazy('assets:asset-list')

    def get_queryset(self):
        self.queryset = super(AssetModalCreateView,self).get_queryset()
        self.s = self.request.GET.get('plain_id_lists')
        if "," in str(self.s):
            self.plain_id_lists = [int(x) for x in self.s.split(',')]
        else:
            self.plain_id_lists = [self.s]
        return self.queryset

    def get_context_data(self, **kwargs):
        asset_on_list = Asset.objects.filter(id__in = self.plain_id_lists)
        context = {
            'app': 'Assets',
            'action': 'Bulk Update asset',
            'assets_on_list': asset_on_list,
            'assets_count': len(asset_on_list),
            'plain_id_lists':self.s,
        }
        kwargs.update(context)
        return super(AssetModalCreateView, self).get_context_data(**kwargs)


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
            'system_users_remain': [system_user for system_user in SystemUser.objects.all()
                                    if system_user not in system_users],
            'system_users': system_users,
        }
        kwargs.update(context)
        return super(AssetDetailView, self).get_context_data(**kwargs)


class AssetModalListView(AdminUserRequiredMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = Asset
    context_object_name = 'asset_modal_list'
    template_name = 'assets/asset_modal_list.html'

    def get_context_data(self, **kwargs):
        group_id = self.request.GET.get('group_id')
        plain_id_lists = self.request.GET.get('plain_id_lists')
        self.s = self.request.GET.get('plain_id_lists')
        assets = Asset.objects.all()
        if "," in str(self.s):
            self.plain_id_lists = [int(x) for x in self.s.split(',')]
        else:
            self.plain_id_lists = [self.s]

        if plain_id_lists:
            if "," in str(self.s):
                plain_id_lists = [int(x) for x in self.s.split(',')]
            else:
                plain_id_lists = [int(self.s)]
            context = {
                'all_assets': plain_id_lists,
            }
            kwargs.update(context)
        if group_id:
            group = AssetGroup.objects.get(id=group_id)
            context = {
                'all_assets': [x.id for x in group.assets.all()],
                'assets': assets
            }
            kwargs.update(context)
        else:
            context = {
                'assets': assets
            }
            kwargs.update(context)
        return super(AssetModalListView, self).get_context_data(**kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class AssetExportView(View):
    def get(self, request, *args, **kwargs):
        spm = request.GET.get('spm', '')
        assets_id = cache.get(spm, [Asset.objects.first().id])
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
        file = form.cleaned_data['file']
        data = file.read().decode('utf-8').strip(
            codecs.BOM_UTF8.decode('utf-8'))
        csv_file = StringIO(data)
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
                    asset = Asset.objects.create(**asset_dict)
                    asset.groups.set(groups)
                    created.append(asset_dict['hostname'])
                    assets.append(asset)
                except IndexError as e:
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
            update_assets_hardware_info.delay(assets)

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


