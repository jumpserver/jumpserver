from django.views.generic import View
from django.shortcuts import render
from django.contrib import messages
from django.utils.translation import ugettext as _

from .forms import EmailSettingForm
from .mixins import AdminUserRequiredMixin


class EmailSettingView(AdminUserRequiredMixin, View):
    form_class = EmailSettingForm
    template_name = "common/email_setting.html"

    def get(self, request):
        context = {
            'app': 'settings',
            'action': 'Email setting',
            "form": EmailSettingForm(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Update email setting successfully"))

        context = {
            'app': 'settings',
            'action': 'Email setting',
            "form": EmailSettingForm(),
        }
        return render(request, self.template_name, context)
