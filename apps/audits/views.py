from django.conf import settings
from django.views.generic import ListView
from django.utils.translation import ugettext as _

from common.mixins import DatetimeSearchMixin
from common.permissions import AdminUserRequiredMixin

from .models import FTPLog


class FTPLogListView(AdminUserRequiredMixin, DatetimeSearchMixin, ListView):
    model = FTPLog
    template_name = 'audits/ftp_log_list.html'
    paginate_by = settings.DISPLAY_PER_PAGE
    user = asset = system_user = filename = ''
    date_from = date_to = None

    def get_queryset(self):
        self.queryset = super().get_queryset()
        self.user = self.request.GET.get('user')
        self.asset = self.request.GET.get('asset')
        self.system_user = self.request.GET.get('system_user')
        self.filename = self.request.GET.get('filename', '')

        filter_kwargs = dict()
        filter_kwargs['date_start__gt'] = self.date_from
        filter_kwargs['date_start__lt'] = self.date_to
        if self.user:
            filter_kwargs['user'] = self.user
        if self.asset:
            filter_kwargs['asset'] = self.asset
        if self.system_user:
            filter_kwargs['system_user'] = self.system_user
        if self.filename:
            filter_kwargs['filename__contains'] = self.filename
        if filter_kwargs:
            self.queryset = self.queryset.filter(**filter_kwargs).order_by('-date_start')
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'user_list': FTPLog.objects.values_list('user', flat=True).distinct(),
            'asset_list': FTPLog.objects.values_list('asset', flat=True).distinct(),
            'system_user_list': FTPLog.objects.values_list('system_user', flat=True).distinct(),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'user': self.user,
            'asset': self.asset,
            'system_user': self.system_user,
            'filename': self.filename,
            "app": _("Audits"),
            "action": _("FTP log"),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
