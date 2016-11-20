# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf import settings
from django.views.generic.list import ListView, MultipleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.detail import DetailView, SingleObjectMixin

from .hands import AdminUserRequiredMixin
from .utils import CreateSudoPrivilegesMixin, ListSudoPrivilegesMixin
from models import *


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

