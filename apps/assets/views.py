# coding:utf-8
from __future__ import absolute_import, unicode_literals
from django.utils.translation import ugettext as _
from django.conf import settings
from django.db.models import Q
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.shortcuts import get_object_or_404, reverse, redirect
from common.utils import int_seq
from .utils import CreateAssetTagsMiXin,UpdateAssetTagsMiXin
from .models import Asset, AssetGroup, IDC, AssetExtend, AdminUser, SystemUser, Tag
from .forms import *
from .hands import AdminUserRequiredMixin


class AssetListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/asset_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'asset list',
            'tag_list': [(i.id, i.name, i.asset_set.all().count())for i in Tag.objects.all().order_by('name')]

        }
        kwargs.update(context)
        return super(AssetListView, self).get_context_data(**kwargs)


class AssetCreateView(AdminUserRequiredMixin, CreateAssetTagsMiXin, CreateView):
    model = Asset
    tag_type = 'asset'
    form_class = AssetCreateForm
    template_name = 'assets/asset_create.html'
    success_url = reverse_lazy('assets:asset-list')

    def form_valid(self, form):
        asset = form.save()
        asset.created_by = self.request.user.username or 'Admin'
        asset.save()
        return super(AssetCreateView, self).form_valid(form)

    def form_invalid(self, form):
        if form.errors.get('__all__'):
            form.errors['all'] = form.errors.get('__all__')
        return super(AssetCreateView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'Create asset',
        }
        kwargs.update(context)
        return super(AssetCreateView, self).get_context_data(**kwargs)


class AssetModalCreateView(AdminUserRequiredMixin, CreateAssetTagsMiXin, ListView):
    model = Asset
    form_class = AssetCreateForm
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


class AssetUpdateView(AdminUserRequiredMixin, UpdateAssetTagsMiXin, UpdateView):
    model = Asset
    form_class = AssetCreateForm
    template_name = 'assets/asset_update.html'
    success_url = reverse_lazy('assets:asset-list')
    new_form = ''
    assets_ids = ''

    def post(self, request, *args, **kwargs):
        default_keys = [
            'csrfmiddlewaretoken',
            'assets_ids',
            'ip',
            'number',
            'hostname',
            'system_users',
            'admin_user',
        ]
        self.assets_ids = self.request.POST.getlist('assets_ids')
        self.new_form = self.request.POST.copy()
        for i in default_keys:
            if self.new_form.has_key(i):
                self.new_form.pop(i)

        return super(AssetUpdateView, self).post(request, *args, **kwargs)

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

    def form_valid(self, form):
        asset = form.save(commit=False)

        def prn_obj_key(obj_form):
            return obj_form.clean().keys()

        for i in prn_obj_key(form):
            if i not in self.new_form.keys():
                print i

                #delattr(asset, '"%s" % i')
                #del asset.i
        asset.save()
        asset.id = 27
        # asset.created_by = self.request.user.username or 'Admin'
        asset.save()
        asset.id = 28
        asset.save()
        return super(AssetUpdateView, self).form_valid(form)


class AssetDeleteView(DeleteView):
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
        tag_id = self.request.GET.get('tag_id')
        plain_id_lists = self.request.GET.get('plain_id_lists')
        self.s = self.request.GET.get('plain_id_lists')
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
                'all_assets' :plain_id_lists
            }
            kwargs.update(context)
        if group_id:
            group = AssetGroup.objects.get(id=group_id)
            context = {
                'all_assets': [x.id for x in group.assets.all()]
            }
            kwargs.update(context)
        if tag_id:
            tag = Tag.objects.get(id=tag_id)
            context = {
                'all_assets': [x.id for x in tag.asset_set.all()]
            }
            kwargs.update(context)
        return super(AssetModalListView, self).get_context_data(**kwargs)


class AssetGroupCreateView(AdminUserRequiredMixin, CreateView):
    model = AssetGroup
    form_class = AssetGroupForm
    template_name = 'assets/asset_group_create.html'
    success_url = reverse_lazy('assets:asset-group-list')
    #ordering = '-id'

    # Todo: Asset group create template select assets so hard, need be resolve next

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create asset group'),
            'assets_count': 0,
        }
        kwargs.update(context)
        return super(AssetGroupCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        asset_group = form.save()
        assets_id_list = self.request.POST.getlist('assets', [])
        assets = [get_object_or_404(Asset, id=int(asset_id)) for asset_id in assets_id_list]
        asset_group.created_by = self.request.user.username or 'Admin'
        asset_group.assets.add(*tuple(assets))
        asset_group.save()
        return super(AssetGroupCreateView, self).form_valid(form)


class AssetGroupListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/asset_group_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Asset group list'),
            'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(AssetGroupListView, self).get_context_data(**kwargs)


class AssetGroupDetailView(AdminUserRequiredMixin, DetailView):
    model = AssetGroup
    template_name = 'assets/asset_group_detail.html'
    context_object_name = 'asset_group'

    def get_context_data(self, **kwargs):
        assets_remain = Asset.objects.exclude(id__in=self.object.assets.all())
        system_users = self.object.system_users.all()
        system_users_remain = SystemUser.objects.exclude(id__in=system_users)
        context = {
            'app': _('Assets'),
            'action': _('Asset group detail'),
            'assets_remain': assets_remain,
            'system_users': system_users,
            'system_users_remain': system_users_remain,
        }
        kwargs.update(context)
        return super(AssetGroupDetailView, self).get_context_data(**kwargs)


class AssetGroupUpdateView(AdminUserRequiredMixin, UpdateView):
    model = AssetGroup
    form_class = AssetGroupForm
    template_name = 'assets/asset_group_create.html'
    success_url = reverse_lazy('assets:asset-group-list')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=AssetGroup.objects.all())
        return super(AssetGroupUpdateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        assets_all = self.object.assets.all()
        context = {
            'app': _('Assets'),
            'action': _('Create asset group'),
            'assets_on_list': assets_all,
            'assets_count': len(assets_all),
            'group_id':self.object.id,
        }
        kwargs.update(context)
        return super(AssetGroupUpdateView, self).get_context_data(**kwargs)


class AssetGroupDeleteView(AdminUserRequiredMixin, DeleteView):
    template_name = 'assets/delete_confirm.html'
    model = AssetGroup
    success_url = reverse_lazy('assets:asset-group-list')


class IDCListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/idc_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('IDC list'),
            # 'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(IDCListView, self).get_context_data(**kwargs)


class IDCCreateView(AdminUserRequiredMixin, CreateView):
    model = IDC
    form_class = IDCForm
    template_name = 'assets/idc_create_update.html'
    success_url = reverse_lazy('assets:idc-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('assets'),
            'action': _('Create IDC'),
        }
        kwargs.update(context)
        return super(IDCCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        IDC = form.save(commit=False)
        IDC.created_by = self.request.user.username or 'System'
        IDC.save()
        # IDC_add_success_next(user)
        return super(IDCCreateView, self).form_valid(form)


class IDCUpdateView(AdminUserRequiredMixin, UpdateView):
    model = IDC
    form_class = IDCForm
    template_name = 'assets/idc_create_update.html'
    context_object_name = 'idc'
    success_url = reverse_lazy('assets:idc-list')

    def form_valid(self, form):
        idc = form.save(commit=False)
        idc.save()
        return super(IDCUpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('assets'),
            'action': _('Update IDC'),
        }
        kwargs.update(context)
        return super(IDCUpdateView, self).get_context_data(**kwargs)


class IDCDetailView(AdminUserRequiredMixin, DetailView):
    model = IDC
    template_name = 'assets/idc_detail.html'
    context_object_name = 'idc'


class IDCAssetsView(AdminUserRequiredMixin, DetailView):
    model = IDC
    template_name = 'assets/idc_assets.html'
    context_object_name = 'idc'


class IDCDeleteView(AdminUserRequiredMixin, DeleteView):
    model = IDC
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('assets:idc-list')


class AdminUserListView(AdminUserRequiredMixin, TemplateView):
    model = AdminUser
    # paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    # context_object_name = 'admin_user_list'
    template_name = 'assets/admin_user_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Admin user list'),
            # 'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(AdminUserListView, self).get_context_data(**kwargs)

    # def get_queryset(self):
    #     Todo: Default order by lose asset connection num
        # self.queryset = super(AdminUserListView, self).get_queryset()
        # self.keyword = keyword = self.request.GET.get('keyword', '')
        # self.sort = sort = self.request.GET.get('sort', '-date_created')
        #
        # if keyword:
        #     self.queryset = self.queryset.filter(Q(name__icontains=keyword) |
        #                                          Q(comment__icontains=keyword))
        #
        # if sort:
        #     self.queryset = self.queryset.order_by(sort)
        # return self.queryset


class AdminUserCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = AdminUser
    form_class = AdminUserForm
    template_name = 'assets/admin_user_create_update.html'
    success_url = reverse_lazy('assets:admin-user-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': 'assets',
            'action': 'Create admin user'
        }
        kwargs.update(context)
        return super(AdminUserCreateView, self).get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        success_message = _('Create admin user <a href="%s">%s</a> successfully.' %
                            (
                                reverse_lazy('assets:admin-user-detail', kwargs={'pk': self.object.pk}),
                                self.object.name,
                            ))
        return success_message

    def form_invalid(self, form):
        return super(AdminUserCreateView, self).form_invalid(form)


class AdminUserUpdateView(AdminUserRequiredMixin, UpdateView):
    model = AdminUser
    form_class = AdminUserForm
    template_name = 'assets/admin_user_create_update.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'assets',
            'action': 'Update admin user'
        }
        kwargs.update(context)
        return super(AdminUserUpdateView, self).get_context_data(**kwargs)

    def get_success_url(self):
        success_url = reverse_lazy('assets:admin-user-detail', pk=self.object.pk)
        return success_url


class AdminUserDetailView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'assets/admin_user_detail.html'
    context_object_name = 'admin_user'

    def get(self, request, *args, **kwargs):
        self.object  = self.get_object(queryset=AdminUser.objects.all())
        return super(AdminUserDetailView, self).get(request, *args, **kwargs)

    # Todo: queryset default order by connectivity, need ops support
    def get_queryset(self):
        return self.object.assets.all()

    def get_context_data(self, **kwargs):
        context = {
            'app': 'assets',
            'action': 'Admin user detail'
        }
        kwargs.update(context)
        return super(AdminUserDetailView, self).get_context_data(**kwargs)


class AdminUserDeleteView(AdminUserRequiredMixin, DeleteView):
    model = AdminUser
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('assets:admin-user-list')


class SystemUserListView(AdminUserRequiredMixin, ListView):
    model = SystemUser
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'system_user_list'
    template_name = 'assets/system_user_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('System user list'),
            'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(SystemUserListView, self).get_context_data(**kwargs)

    def get_queryset(self):
        # Todo: Default order by lose asset connection num
        self.queryset = super(SystemUserListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort', '-date_created')

        if keyword:
            self.queryset = self.queryset.filter(Q(name__icontains=keyword) |
                                                 Q(comment__icontains=keyword))

        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset


class SystemUserCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = SystemUser
    form_class = SystemUserForm
    template_name = 'assets/system_user_create_update.html'
    success_url = reverse_lazy('assets:system-user-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create system user'),
        }
        kwargs.update(context)
        return super(SystemUserCreateView, self).get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        success_message = _('Create system user <a href="%s">%s</a> successfully.' %
                            (
                                reverse_lazy('assets:system-user-detail', kwargs={'pk': self.object.pk}),
                                self.object.name,
                            ))

        return success_message


class SystemUserUpdateView(AdminUserRequiredMixin, UpdateView):
    model = SystemUser
    form_class = SystemUserForm
    template_name = 'assets/system_user_create_update.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update system user')
        }
        kwargs.update(context)
        return super(SystemUserUpdateView, self).get_context_data(**kwargs)

    def get_success_url(self):
        success_url = reverse_lazy('assets:system-user-detail', kwargs={'pk': self.object.pk})
        return success_url


class SystemUserDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'assets/system_user_detail.html'
    context_object_name = 'system_user'
    model = SystemUser

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('System user detail')
        }
        kwargs.update(context)
        return super(SystemUserDetailView, self).get_context_data(**kwargs)


class SystemUserDeleteView(AdminUserRequiredMixin, DeleteView):
    model = SystemUser
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('assets:system-user-list')


class SystemUserAssetView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'assets/system_user_asset.html'
    context_object_name = 'system_user'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=SystemUser.objects.all())
        return super(SystemUserAssetView, self).get(request, *args, **kwargs)

    def get_asset_groups(self):
        return self.object.asset_groups.all()

    # Todo: queryset default order by connectivity, need ops support
    def get_queryset(self):
        return list(self.object.get_assets())

    def get_context_data(self, **kwargs):
        asset_groups = self.get_asset_groups()
        assets = self.get_queryset()
        context = {
            'app': 'assets',
            'action': 'System user asset',
            'assets_remain': [asset for asset in Asset.objects.all() if asset not in assets],
            'asset_groups': asset_groups,
            'asset_groups_remain': [asset_group for asset_group in AssetGroup.objects.all()
                                    if asset_group not in asset_groups]
        }
        kwargs.update(context)
        return super(SystemUserAssetView, self).get_context_data(**kwargs)


class TagView(ListView):
    context_object_name = 'asset_list'
    template_name = 'assets/asset_list.html'

    def get_queryset(self):
        asset_list = Asset.objects.filter(tags=self.kwargs['tag_id'])
        return asset_list

    def get_context_data(self, **kwargs):
        kwargs['app'] = 'Assets'
        kwargs['action']='asset list'
        kwargs['tag_list'] =  [(i.id,i.name,i.asset_set.all().count() )for i in Tag.objects.all().order_by('name')]
        kwargs['tag_id'] = self.kwargs['tag_id']
        return super(TagView, self).get_context_data(**kwargs)


class TagsListView(AdminUserRequiredMixin, ListView):
    model = Tag
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'asset_tags_list'
    template_name = 'assets/asset_tags_list.html'
    ordering = '-id'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Tag'),
            'action': _('Asset Tags list'),
            'keyword': self.request.GET.get('keyword', '')
        }
        kwargs.update(context)
        return super(TagsListView, self).get_context_data(**kwargs)


class AssetTagCreateView(AdminUserRequiredMixin, CreateView):
    model = Tag
    form_class = AssetTagForm
    template_name = 'assets/asset_tag_create.html'
    success_url = reverse_lazy('assets:asset-tag-list')
    #ordering = '-id'

    # Todo: Asset group create template select assets so hard, need be resolve next

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Tag'),
            'action': _('Asset Tags list'),
            'assets_count': 0,
        }
        kwargs.update(context)
        return super(AssetTagCreateView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        asset_tag = form.save()
        assets_id_list = self.request.POST.getlist('assets', [])
        assets = [get_object_or_404(Asset, id=int(asset_id)) for asset_id in assets_id_list]
        asset_tag.created_by = self.request.user.username or 'Admin'
        asset_tag.asset_set.add(*tuple(assets))
        asset_tag.save()
        return super(AssetTagCreateView, self).form_valid(form)


class AssetTagDetailView(SingleObjectMixin, AdminUserRequiredMixin, ListView):
    template_name = 'assets/asset_tag_detail.html'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=Tag.objects.all())
        return super(AssetTagDetailView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return self.object.asset_set.all()

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Tag'),
            'action': _('Asset Tags detail'),
            'asset_tag': self.object,
        }
        kwargs.update(context)
        return super(AssetTagDetailView, self).get_context_data(**kwargs)


class AssetTagUpdateView(AdminUserRequiredMixin, UpdateView):
    model = Tag
    form_class = AssetTagForm
    template_name = 'assets/asset_tag_create.html'
    success_url = reverse_lazy('assets:asset-tag-list')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=Tag.objects.all())
        return super(AssetTagUpdateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        assets_all = self.object.asset_set.all()
        context = {
            'app': _('Tag'),
            'action': _('Asset Tags detail'),
            'assets_count': len(assets_all),
            'assets_on_list': assets_all,
            'tag_id':self.object.id,
        }
        kwargs.update(context)
        return super(AssetTagUpdateView, self).get_context_data(**kwargs)


class AssetTagDeleteView(AdminUserRequiredMixin, DeleteView):
    template_name = 'assets/delete_confirm.html'
    model = Tag
    success_url = reverse_lazy('assets:asset-tag-list')

