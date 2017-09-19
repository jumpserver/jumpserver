from django.utils.translation import ugettext as _
from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.edit import DeleteView
from django.views.generic.detail import DetailView
from .models import ApplyPermission
from .forms import ApplyPermissionForm
from django.conf import settings
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.db import transaction
class ApplyPermissionListView(ListView):
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
        self.queryset = super(ApplyPermissionListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort', '-date_applied')

        if keyword:
            self.queryset = self.queryset\
                .filter(Q(users__name__contains=keyword) |
                        Q(users__approver__contains=keyword) |
                        Q(user_status__contains=keyword)).distinct()
        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset


class ApplyPermissionCreateView(SuccessMessageMixin,
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

    def form_valid(self, form):
        assets = form.cleaned_data['assets']
        asset_groups = form.cleaned_data['asset_groups']
        system_users = form.cleaned_data['system_users']
        associate_system_users_and_assets(system_users, assets, asset_groups)
        response = super(AssetPermissionCreateView, self).form_valid(form)
        self.object.created_by = self.request.user.name
        self.object.save()
        return response

class ApplyPermissionUpdateView(UpdateView):
    pass

class ApplyPermissionDeleteView(DeleteView):
    pass

class ApplyPermissionDetailView(DetailView):
    pass