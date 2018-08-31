from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.conf import settings

from .forms import EmailSettingForm, LDAPSettingForm, BasicSettingForm, \
    TerminalSettingForm, SecuritySettingForm
from common.permissions import SuperUserRequiredMixin
from .signals import ldap_auth_enable


class BasicSettingView(SuperUserRequiredMixin, TemplateView):
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
            msg = _("Update setting successfully, please restart program")
            messages.success(request, msg)
            return redirect('settings:basic-setting')
        else:
            context = self.get_context_data()
            context.update({"form": form})
            return render(request, self.template_name, context)


class EmailSettingView(SuperUserRequiredMixin, TemplateView):
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


class LDAPSettingView(SuperUserRequiredMixin, TemplateView):
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
            if "AUTH_LDAP" in form.cleaned_data:
                ldap_auth_enable.send(sender=self.__class__, enabled=form.cleaned_data["AUTH_LDAP"])
            msg = _("Update setting successfully, please restart program")
            messages.success(request, msg)
            return redirect('settings:ldap-setting')
        else:
            context = self.get_context_data()
            context.update({"form": form})
            return render(request, self.template_name, context)


class TerminalSettingView(SuperUserRequiredMixin, TemplateView):
    form_class = TerminalSettingForm
    template_name = "common/terminal_setting.html"

    def get_context_data(self, **kwargs):
        command_storage = settings.TERMINAL_COMMAND_STORAGE
        replay_storage = settings.TERMINAL_REPLAY_STORAGE
        context = {
            'app': _('Settings'),
            'action': _('Terminal setting'),
            'form': self.form_class(),
            'replay_storage': replay_storage,
            'command_storage': command_storage,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            msg = _("Update setting successfully, please restart program")
            messages.success(request, msg)
            return redirect('settings:terminal-setting')
        else:
            context = self.get_context_data()
            context.update({"form": form})
            return render(request, self.template_name, context)


class SecuritySettingView(SuperUserRequiredMixin, TemplateView):
    form_class = SecuritySettingForm
    template_name = "common/security_setting.html"

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Settings'),
            'action': _('Security setting'),
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
            return redirect('settings:security-setting')
        else:
            context = self.get_context_data()
            context.update({"form": form})
            return render(request, self.template_name, context)
