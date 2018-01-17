from django.views.generic import View, TemplateView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import ugettext as _

from .forms import EmailSettingForm, LDAPSettingForm, BasicSettingForm
from .models import Setting
from .mixins import AdminUserRequiredMixin
from .signals import ldap_auth_enable


class BasicSettingView(AdminUserRequiredMixin, TemplateView):
    form_class = BasicSettingForm
    template_name = "common/basic_setting.html"

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Settings'),
            'action': _('Basic setting'),
            'form': self.form_class(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            if "AUTH_LDAP" in form.cleaned_data:
                ldap_auth_enable.send(form.cleaned_data["AUTH_LDAP"])
            msg = _("Update setting successfully, please restart program")
            messages.success(request, msg)
            return redirect('settings:basic-setting')
        else:
            context = self.get_context_data()
            context.update({"form": form})
            return render(request, self.template_name, context)


class EmailSettingView(AdminUserRequiredMixin, TemplateView):
    form_class = EmailSettingForm
    template_name = "common/email_setting.html"

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Settings'),
            'action': _('Email setting'),
            'form': self.form_class(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            msg = _("Update setting successfully, please restart program")
            messages.success(request, msg)
            return redirect('settings:email-setting')
        else:
            context = self.get_context_data()
            context.update({"form": form})
            return render(request, self.template_name, context)


class LDAPSettingView(AdminUserRequiredMixin, TemplateView):
    form_class = LDAPSettingForm
    template_name = "common/ldap_setting.html"

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Settings'),
            'action': _('LDAP setting'),
            'form': self.form_class(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            msg = _("Update setting successfully, please restart program")
            messages.success(request, msg)
            return redirect('settings:ldap-setting')
        else:
            context = self.get_context_data()
            context.update({"form": form})
            return render(request, self.template_name, context)


class StorageSettingView(AdminUserRequiredMixin, TemplateView):
    form_class = LDAPSettingForm
    template_name = "common/storage_setting.html"

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Settings'),
            'action': _('Storage setting'),
            'form': self.form_class(),
            'command_storage': Setting.objects.filter(name__endswith="_COMMAND_STORAGE")
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            msg = _("Update setting successfully, please restart program")
            messages.success(request, msg)
            return redirect('settings:storage-setting')
        else:
            context = self.get_context_data()
            context.update({"form": form})
            return render(request, self.template_name, context)
