# coding:utf-8
from __future__ import absolute_import, unicode_literals

import csv
import json
import uuid
import codecs
import chardet
from io import StringIO

from django.db import transaction
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib.messages.views import SuccessMessageMixin

from common.mixins import JSONResponseMixin
from common.utils import get_object_or_none, get_logger
from common.permissions import AdminUserRequiredMixin
from common.const import (
    create_success_msg, update_success_msg, KEY_CACHE_RESOURCES_ID
)
from ..const import CACHE_KEY_ASSET_BULK_UPDATE_ID_PREFIX
from orgs.utils import current_org
from .. import forms
from ..models import Asset, AdminUser, SystemUser, Label, Node, Domain


__all__ = [
    'AssetListView', 'AssetCreateView', 'AssetUpdateView', 'AssetUserListView',
    'UserAssetListView', 'AssetBulkUpdateView', 'AssetDetailView',
    'AssetDeleteView', 'AssetExportView', 'BulkImportAssetView',
]
logger = get_logger(__file__)


class AssetListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/asset_list.html'

    def get_context_data(self, **kwargs):
        Node.root()
        context = {
            'app': _('Assets'),
            'action': _('Asset list'),
            'labels': Label.objects.all().order_by('name'),
            'nodes': Node.objects.all().order_by('-key'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetUserListView(AdminUserRequiredMixin, DetailView):
    model = Asset
    context_object_name = 'asset'
    template_name = 'assets/asset_asset_user_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Asset user list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserAssetListView(LoginRequiredMixin, TemplateView):
    template_name = 'assets/user_asset_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'action': _('My assets'),
            'labels': Label.objects.all().order_by('name'),
            'system_users': SystemUser.objects.all(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = Asset
    form_class = forms.AssetCreateForm
    template_name = 'assets/asset_create.html'
    success_url = reverse_lazy('assets:asset-list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        node_id = self.request.GET.get("node_id")
        if node_id:
            node = get_object_or_none(Node, id=node_id)
        else:
            node = Node.root()
        form["nodes"].initial = node
        return form

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create asset'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        return create_success_msg % ({"name": cleaned_data["hostname"]})


class AssetBulkUpdateView(AdminUserRequiredMixin, ListView):
    model = Asset
    form_class = forms.AssetBulkUpdateForm
    template_name = 'assets/asset_bulk_update.html'
    success_url = reverse_lazy('assets:asset-list')
    success_message = _("Bulk update asset success")
    id_list = None
    form = None

    def get(self, request, *args, **kwargs):
        spm = request.GET.get('spm', '')
        assets_id = cache.get(KEY_CACHE_RESOURCES_ID.format(spm))
        if kwargs.get('form'):
            self.form = kwargs['form']
        elif assets_id:
            self.form = self.form_class(initial={'assets': assets_id})
        else:
            self.form = self.form_class()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, self.success_message)
            return redirect(self.success_url)
        else:
            return self.get(request, form=form, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Bulk update asset'),
            'form': self.form,
            'assets_selected': self.id_list,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Asset
    form_class = forms.AssetUpdateForm
    template_name = 'assets/asset_update.html'
    success_url = reverse_lazy('assets:asset-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update asset'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        return update_success_msg % ({"name": cleaned_data["hostname"]})


class AssetDeleteView(AdminUserRequiredMixin, DeleteView):
    model = Asset
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('assets:asset-list')


class AssetDetailView(LoginRequiredMixin, DetailView):
    model = Asset
    context_object_name = 'asset'
    template_name = 'assets/asset_detail.html'

    def get_context_data(self, **kwargs):
        nodes_remain = Node.objects.exclude(assets=self.object)
        context = {
            'app': _('Assets'),
            'action': _('Asset detail'),
            'nodes_remain': nodes_remain,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class AssetExportView(LoginRequiredMixin, View):
    def get(self, request):
        spm = request.GET.get('spm', '')
        assets_id_default = [Asset.objects.first().id] if Asset.objects.first() else []
        assets_id = cache.get(spm, assets_id_default)
        fields = [
            field for field in Asset._meta.fields
            if field.name not in [
                'date_created', 'org_id'
            ]
        ]
        filename = 'assets-{}.csv'.format(
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(codecs.BOM_UTF8)
        assets = Asset.objects.filter(id__in=assets_id)
        writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_MINIMAL)

        header = [field.verbose_name for field in fields]
        writer.writerow(header)

        for asset in assets:
            data = [getattr(asset, field.name) for field in fields]
            writer.writerow(data)
        return response

    def post(self, request, *args, **kwargs):
        try:
            assets_id = json.loads(request.body).get('assets_id', [])
            node_id = json.loads(request.body).get('node_id', None)
        except ValueError:
            return HttpResponse('Json object not valid', status=400)

        if not assets_id:
            node = get_object_or_none(Node, id=node_id) if node_id else Node.root()
            assets = node.get_all_assets()
            for asset in assets:
                assets_id.append(asset.id)

        spm = uuid.uuid4().hex
        cache.set(spm, assets_id, 300)
        url = reverse_lazy('assets:asset-export') + '?spm=%s' % spm
        return JsonResponse({'redirect': url})


class BulkImportAssetView(AdminUserRequiredMixin, JSONResponseMixin, FormView):
    form_class = forms.FileForm

    def form_valid(self, form):
        node_id = self.request.GET.get("node_id")
        node = get_object_or_none(Node, id=node_id) if node_id else Node.root()
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

            asset_dict_raw = dict(zip(attr, row))
            asset_dict = dict()
            for k, v in asset_dict_raw.items():
                v = v.strip()
                if k == 'is_active':
                    v = False if v in ['False', 0, 'false'] else True
                elif k == 'admin_user':
                    v = get_object_or_none(AdminUser, name=v)
                elif k in ['port', 'cpu_count', 'cpu_cores']:
                    try:
                        v = int(v)
                    except ValueError:
                        v = ''
                elif k == 'domain':
                    v = get_object_or_none(Domain, name=v)
                elif k == 'platform':
                    v = v.lower().capitalize()
                if v != '':
                    asset_dict[k] = v

            asset = None
            asset_id = asset_dict.pop('id', None)
            if asset_id:
                asset = get_object_or_none(Asset, id=asset_id)
            if not asset:
                try:
                    if len(Asset.objects.filter(hostname=asset_dict.get('hostname'))):
                        raise Exception(_('already exists'))
                    with transaction.atomic():
                        asset = Asset.objects.create(**asset_dict)
                        if node:
                            asset.nodes.set([node])
                        created.append(asset_dict['hostname'])
                        assets.append(asset)
                except Exception as e:
                    failed.append('%s: %s' % (asset_dict['hostname'], str(e)))
            else:
                for k, v in asset_dict.items():
                    if v != '':
                        setattr(asset, k, v)
                try:
                    asset.save()
                    updated.append(asset_dict['hostname'])
                except Exception as e:
                    failed.append('%s: %s' % (asset_dict['hostname'], str(e)))

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

