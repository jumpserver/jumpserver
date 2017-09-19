from django.utils.translation import ugettext as _
from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.edit import DeleteView
from django.views.generic.detail import DetailView
from .models import ApplyPermission
from django.conf import settings

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


class ApplyPermissionCreateView(CreateView):
    pass

class ApplyPermissionUpdateView(UpdateView):
    pass

class ApplyPermissionDeleteView(DeleteView):
    pass

class ApplyPermissionDetailView(DetailView):
    pass