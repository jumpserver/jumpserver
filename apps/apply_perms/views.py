from django.utils.translation import ugettext as _
from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, View
from django.views.generic.edit import DeleteView
from django.views.generic.detail import DetailView
from .models import ApplyPermission
from .forms import ApplyPermissionForm
from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.db import transaction
import json
from django.utils import timezone
from assets.models import Asset
from users.utils import ApplyUserRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import reverse, redirect

class ApplyPermissionListView(LoginRequiredMixin, ListView):
    model = ApplyPermission
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'apply_permission_list'
    template_name = 'apply_perms/apply_permission_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Apply permission'),
            'action': _('Apply permission list'),
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super(ApplyPermissionListView, self).get_context_data(**kwargs)

    def get_queryset(self):
        usr = self.request.user
        if usr.is_superuser:
            self.queryset = super(ApplyPermissionListView, self).get_queryset()
        elif usr.is_groupadmin:
            self.queryset = usr.apply_permissions.all() | usr.approval_tasks.all()
        elif usr.is_commonuser:
            self.queryset = usr.apply_permissions.all()

        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort', '-date_applied')
        if keyword:
            self.queryset = self.queryset\
                .filter(Q(applicant__username__contains=keyword) |
                        Q(approver__username__contains=keyword) |
                        Q(status=keyword)).distinct()
        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset


class ApplyPermissionCreateView(ApplyUserRequiredMixin,
                                SuccessMessageMixin,
                                CreateView):
    model = ApplyPermission
    form_class = ApplyPermissionForm
    template_name = 'apply_perms/apply_permission_create_update.html'
    success_url = reverse_lazy('apply-perms:apply-permission-list')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        return super(ApplyPermissionCreateView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Apply permission'),
            'action': _('Create apply permission'),
        }
        kwargs.update(context)
        return super(ApplyPermissionCreateView, self).get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        url = reverse_lazy('apply-perms:apply-permission-detail',
                           kwargs={'pk': self.object.pk})
        success_message = _(
            'Create apply permission <a href="{url}"> {name} </a> '
            'successfully.'.format(url=url, name=self.object.name))
        return success_message

    def get_form_kwargs(self):
        kwargs = super(ApplyPermissionCreateView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
        })
        return kwargs

    def form_valid(self, form):
        obj = form.instance
        obj.date_applied = timezone.localtime()
        obj.applicant = self.request.user
        obj.user_groups = list(user_group.id for user_group in form.cleaned_data['user_groups'])
        obj.assets = list(asset.id for asset in form.cleaned_data['assets'])
        obj.asset_groups = list(asset_group.id for asset_group in form.cleaned_data['asset_groups'])
        obj.system_users = list(system_user.id for system_user in form.cleaned_data['system_users'])
        obj.save()
        return super(ApplyPermissionCreateView, self).form_valid(form)

    # def form_invalid(self, form):
    #     form.add_error('name', 'Invalid Data.')
    #     return super(ApplyPermissionCreateView, self).form_invalid(form)

class ApplyPermissionUpdateView(LoginRequiredMixin,
                                UpdateView):
    model = ApplyPermission
    form_class = ApplyPermissionForm
    template_name = 'apply_perms/apply_permission_create_update.html'
    success_url = reverse_lazy('apply-perms:apply-permission-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Apply permission'),
            'action': _('Update apply permission'),
        }
        kwargs.update(context)
        return super(ApplyPermissionUpdateView, self).get_context_data(**kwargs)

    def get_form_kwargs(self):
        kwargs = super(ApplyPermissionUpdateView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
        })
        return kwargs

    def form_valid(self, form):
        obj = form.instance
        obj.user_groups = list(user_group.id for user_group in form.cleaned_data['user_groups'])
        obj.assets = list(asset.id for asset in form.cleaned_data['assets'])
        obj.asset_groups = list(asset_group.id for asset_group in form.cleaned_data['asset_groups'])
        obj.system_users = list(system_user.id for system_user in form.cleaned_data['system_users'])
        obj.save()
        return super(ApplyPermissionUpdateView, self).form_valid(form)

class ApplyPermissionDeleteView(LoginRequiredMixin, DeleteView):
    pass

class ApplyPermissionDetailView(LoginRequiredMixin, DetailView):
    pass