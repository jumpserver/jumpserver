from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.conf import settings

from .forms import EmailSettingForm, LDAPSettingForm, BasicSettingForm, \
    TerminalSettingForm, SecuritySettingForm, StorageSettingForm
from common.permissions import SuperUserRequiredMixin
from .signals import ldap_auth_enable
import json


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


class StorageSettingView(SuperUserRequiredMixin, TemplateView):
    form_class = StorageSettingForm
    template_name = "common/storage_setting.html"

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Settings'),
            'action': _('Storage setting'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        get_body = request.GET
        setting_name = get_body.get("setting_name", '')
        setting_data = get_body.get("storage_info", None)

        if setting_data is not None:
            setting_dict = json.loads(setting_data, encoding='utf-8')
        else:
            setting_dict = {}

        context = self.get_context_data(**kwargs)
        form = self.form_class()
        form.set_setting_name(setting_name)
        form.set_initial(setting_dict)
        context.update({"form": form})

        context["setting_name"] = setting_name
        if setting_name == "TERMINAL_COMMAND_STORAGE":
            context['action'] = "Command storage setting"
        elif setting_name == "TERMINAL_REPLAY_STORAGE":
            context['action'] = "Replay storage setting"

        return self.render_to_response(context)

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

