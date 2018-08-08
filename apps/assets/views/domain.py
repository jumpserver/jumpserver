# -*- coding: utf-8 -*-
#

from django.views.generic import TemplateView, CreateView, \
    UpdateView, DeleteView, DetailView
from django.views.generic.detail import SingleObjectMixin
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse_lazy, reverse

from common.permissions import AdminUserRequiredMixin
from common.const import create_success_msg, update_success_msg
from common.utils import get_object_or_none
from ..models import Domain, Gateway
from ..forms import DomainForm, GatewayForm


__all__ = (
    "DomainListView", "DomainCreateView", "DomainUpdateView",
    "DomainDetailView", "DomainDeleteView", "DomainGatewayListView",
    "DomainGatewayCreateView", 'DomainGatewayUpdateView',
)


class DomainListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/domain_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Domain list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DomainCreateView(AdminUserRequiredMixin, CreateView):
    model = Domain
    template_name = 'assets/domain_create_update.html'
    form_class = DomainForm
    success_url = reverse_lazy('assets:domain-list')
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create domain'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DomainUpdateView(AdminUserRequiredMixin, UpdateView):
    model = Domain
    template_name = 'assets/domain_create_update.html'
    form_class = DomainForm
    success_url = reverse_lazy('assets:domain-list')
    success_message = update_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update domain'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DomainDetailView(AdminUserRequiredMixin, DetailView):
    model = Domain
    template_name = 'assets/domain_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Domain detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DomainDeleteView(AdminUserRequiredMixin, DeleteView):
    model = Domain
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('assets:domain-list')


class DomainGatewayListView(AdminUserRequiredMixin, SingleObjectMixin, TemplateView):
    template_name = 'assets/domain_gateway_list.html'
    model = Domain
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=self.model.objects.all())
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Domain gateway list'),
            'object': self.get_object()
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DomainGatewayCreateView(AdminUserRequiredMixin, CreateView):
    model = Gateway
    template_name = 'assets/gateway_create_update.html'
    form_class = GatewayForm
    success_message = create_success_msg

    def get_success_url(self):
        domain = self.object.domain
        return reverse('assets:domain-gateway-list', kwargs={"pk": domain.id})

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        domain_id = self.kwargs.get("pk")
        domain = get_object_or_none(Domain, id=domain_id)
        if domain:
            form['domain'].initial = domain
        return form

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create gateway'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class DomainGatewayUpdateView(AdminUserRequiredMixin, UpdateView):
    model = Gateway
    template_name = 'assets/gateway_create_update.html'
    form_class = GatewayForm
    success_message = update_success_msg

    def get_success_url(self):
        domain = self.object.domain
        return reverse('assets:domain-gateway-list', kwargs={"pk": domain.id})

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update gateway'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
