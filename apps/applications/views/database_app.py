# coding: utf-8
#

from django.http import Http404
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.utils.translation import ugettext_lazy as _
from django.views.generic.detail import DetailView

from common.permissions import PermissionsMixin, IsOrgAdmin, IsValidUser

from .. import models, const, forms

__all__ = [
    'DatabaseAppListView', 'DatabaseAppCreateView', 'DatabaseAppUpdateView',
    'DatabaseAppDetailView', 'UserDatabaseAppListView',
]


class DatabaseAppListView(PermissionsMixin, TemplateView):
    template_name = 'applications/database_app_list.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _("Application"),
            'action': _('DatabaseApp list'),
            'type_choices': const.DATABASE_APP_TYPE_CHOICES
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class BaseDatabaseAppCreateUpdateView:
    template_name = 'applications/database_app_create_update.html'
    model = models.DatabaseApp
    permission_classes = [IsOrgAdmin]
    default_type = const.DATABASE_APP_TYPE_MYSQL
    form_class = forms.DatabaseAppMySQLForm
    form_class_choices = {
        const.DATABASE_APP_TYPE_MYSQL: forms.DatabaseAppMySQLForm,
    }

    def get_initial(self):
        return {'type': self.get_type()}

    def get_type(self):
        return self.default_type

    def get_form_class(self):
        tp = self.get_type()
        form_class = self.form_class_choices.get(tp)
        if not form_class:
            raise Http404()
        return form_class


class DatabaseAppCreateView(BaseDatabaseAppCreateUpdateView, CreateView):

    def get_type(self):
        tp = self.request.GET.get("type")
        if tp:
            return tp.lower()
        return super().get_type()

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Applications'),
            'action': _('Create DatabaseApp'),
            'api_action': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppUpdateView(BaseDatabaseAppCreateUpdateView, UpdateView):

    def get_type(self):
        return self.object.type

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Applications'),
            'action': _('Create DatabaseApp'),
            'api_action': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DatabaseAppDetailView(PermissionsMixin, DetailView):
    template_name = 'applications/database_app_detail.html'
    model = models.DatabaseApp
    context_object_name = 'database_app'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Applications'),
            'action': _('DatabaseApp detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserDatabaseAppListView(PermissionsMixin, TemplateView):
    template_name = 'applications/user_database_app_list.html'
    permission_classes = [IsValidUser]

    def get_context_data(self, **kwargs):
        context = {
            'action': _('My DatabaseApp'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
