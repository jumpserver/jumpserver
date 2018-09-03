from django.conf import settings
from django.views.generic import ListView
from django.utils.translation import ugettext as _
from django.db.models import Q

from common.mixins import DatetimeSearchMixin
from common.permissions import AdminUserRequiredMixin

from orgs.utils import current_org
from .models import FTPLog, OperateLog, PasswordChangeLog, UserLoginLog


def get_resource_type_list():
    from users.models import User, UserGroup
    from assets.models import Asset, Node, AdminUser, SystemUser, Domain, Gateway
    from orgs.models import Organization
    from perms.models import AssetPermission

    models = [
        User, UserGroup, Asset, Node, AdminUser, SystemUser, Domain,
        Gateway, Organization, AssetPermission
    ]
    return [model._meta.verbose_name for model in models]


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


class OperateLogListView(AdminUserRequiredMixin, DatetimeSearchMixin, ListView):
    model = OperateLog
    template_name = 'audits/operate_log_list.html'
    paginate_by = settings.DISPLAY_PER_PAGE
    user = action = resource_type = ''
    date_from = date_to = None
    actions_dict = dict(OperateLog.ACTION_CHOICES)

    def get_queryset(self):
        self.queryset = super().get_queryset()
        self.user = self.request.GET.get('user')
        self.action = self.request.GET.get('action')
        self.resource_type = self.request.GET.get('resource_type')

        filter_kwargs = dict()
        filter_kwargs['datetime__gt'] = self.date_from
        filter_kwargs['datetime__lt'] = self.date_to
        if self.user:
            filter_kwargs['user'] = self.user
        if self.action:
            filter_kwargs['action'] = self.action
        if self.resource_type:
            filter_kwargs['resource_type'] = self.resource_type
        if filter_kwargs:
            self.queryset = self.queryset.filter(**filter_kwargs).order_by('-datetime')
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'user_list': current_org.get_org_users(),
            'actions': self.actions_dict,
            'resource_type_list': get_resource_type_list(),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'user': self.user,
            'action': self.action,
            'resource_type': self.resource_type,
            "app": _("Audits"),
            "action": _("Operate log"),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class PasswordChangeLogList(AdminUserRequiredMixin, DatetimeSearchMixin, ListView):
    model = PasswordChangeLog
    template_name = 'audits/password_change_log_list.html'
    paginate_by = settings.DISPLAY_PER_PAGE
    user = ''
    date_from = date_to = None

    def get_queryset(self):
        self.queryset = super().get_queryset()
        self.user = self.request.GET.get('user')

        filter_kwargs = dict()
        filter_kwargs['datetime__gt'] = self.date_from
        filter_kwargs['datetime__lt'] = self.date_to
        if self.user:
            filter_kwargs['user'] = self.user
        if filter_kwargs:
            self.queryset = self.queryset.filter(**filter_kwargs).order_by('-datetime')
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'user_list': current_org.get_org_users(),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'user': self.user,
            "app": _("Audits"),
            "action": _("Password change log"),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class LoginLogListView(AdminUserRequiredMixin, DatetimeSearchMixin, ListView):
    template_name = 'audits/login_log_list.html'
    model = UserLoginLog
    paginate_by = settings.DISPLAY_PER_PAGE
    user = keyword = ""
    date_to = date_from = None

    @staticmethod
    def get_org_users():
        users = current_org.get_org_users().values_list('username', flat=True)
        return users

    def get_queryset(self):
        users = self.get_org_users()
        queryset = super().get_queryset().filter(username__in=users)
        self.user = self.request.GET.get('user', '')
        self.keyword = self.request.GET.get("keyword", '')

        queryset = queryset.filter(
            datetime__gt=self.date_from, datetime__lt=self.date_to
        )
        if self.user:
            queryset = queryset.filter(username=self.user)
        if self.keyword:
            queryset = queryset.filter(
                Q(ip__contains=self.keyword) |
                Q(city__contains=self.keyword) |
                Q(username__contains=self.keyword)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('Login log'),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'user': self.user,
            'keyword': self.keyword,
            'user_list': self.get_org_users(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)