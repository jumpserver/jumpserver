# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf import settings
from django.views.generic.list import ListView, MultipleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.detail import DetailView, SingleObjectMixin

from users.utils import AdminUserRequiredMixin
from ops.utils.mixins import CreateSudoPrivilegesMixin, ListSudoPrivilegesMixin
from ops.models import  *


class SudoListView(AdminUserRequiredMixin, ListSudoPrivilegesMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = Sudo
    context_object_name = 'sudos'
    template_name = 'sudo/list.html'


class SudoCreateView(AdminUserRequiredMixin, CreateSudoPrivilegesMixin, CreateView):
    model = Sudo
    template_name = 'sudo/create.html'


class SudoUpdateView(AdminUserRequiredMixin, UpdateView):
    model = Sudo
    template_name = 'sudo/update.html'


class SudoDetailView(DetailView):
    model = Sudo
    context_object_name = 'sudo'
    template_name = 'sudo/detail.html'


class CronListView(AdminUserRequiredMixin, ListSudoPrivilegesMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = CronTable
    context_object_name = 'crons'
    template_name = 'sudo/list.html'


class CronCreateView(AdminUserRequiredMixin, CreateSudoPrivilegesMixin, CreateView):
    model = CronTable
    template_name = 'cron/create.html'


class CronUpdateView(AdminUserRequiredMixin, UpdateView):
    model = CronTable
    template_name = 'cron/update.html'


class CronDetailView(DetailView):
    model = CronTable
    context_object_name = 'cron'
    template_name = 'cron/detail.html'

