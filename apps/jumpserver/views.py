import datetime
import re

from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.views.generic import TemplateView, View
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db.models import Count
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri

from users.models import User
from assets.models import Asset
from terminal.models import Session
from orgs.utils import current_org


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    session_week = None
    session_month = None
    session_month_dates = []
    session_month_dates_archive = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_org_admin:
            return redirect('assets:user-asset-list')
        if not current_org or not current_org.can_admin_by(request.user):
            return redirect('orgs:switch-a-org')
        return super(IndexView, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def get_user_count():
        return current_org.get_org_users().count()

    @staticmethod
    def get_asset_count():
        return Asset.objects.all().count()

    @staticmethod
    def get_online_user_count():
        return len(set(Session.objects.filter(is_finished=False).values_list('user', flat=True)))

    @staticmethod
    def get_online_session_count():
        return Session.objects.filter(is_finished=False).count()

    def get_top5_user_a_week(self):
        return self.session_week.values('user').annotate(total=Count('user')).order_by('-total')[:5]

    def get_week_login_user_count(self):
        return self.session_week.values('user').distinct().count()

    def get_week_login_asset_count(self):
        return self.session_week.count()

    def get_month_day_metrics(self):
        month_str = [d.strftime('%m-%d') for d in self.session_month_dates] or ['0']
        return month_str

    def get_month_login_metrics(self):
        data = []
        time_min = datetime.datetime.min.time()
        time_max = datetime.datetime.max.time()
        for d in self.session_month_dates:
            ds = datetime.datetime.combine(d, time_min).replace(tzinfo=timezone.get_current_timezone())
            de = datetime.datetime.combine(d, time_max).replace(tzinfo=timezone.get_current_timezone())
            data.append(self.session_month.filter(date_start__range=(ds, de)).count())
        return data

    def get_month_active_user_metrics(self):
        if self.session_month_dates_archive:
            return [q.values('user').distinct().count()
                    for q in self.session_month_dates_archive]
        else:
            return [0]

    def get_month_active_asset_metrics(self):
        if self.session_month_dates_archive:
            return [q.values('asset').distinct().count()
                    for q in self.session_month_dates_archive]
        else:
            return [0]

    def get_month_active_user_total(self):
        return self.session_month.values('user').distinct().count()

    def get_month_inactive_user_total(self):
        return current_org.get_org_users().count() - self.get_month_active_user_total()

    def get_month_active_asset_total(self):
        return self.session_month.values('asset').distinct().count()

    def get_month_inactive_asset_total(self):
        return Asset.objects.all().count() - self.get_month_active_asset_total()

    @staticmethod
    def get_user_disabled_total():
        return current_org.get_org_users().filter(is_active=False).count()

    @staticmethod
    def get_asset_disabled_total():
        return Asset.objects.filter(is_active=False).count()

    def get_week_top10_asset(self):
        assets = list(self.session_week.values('asset').annotate(total=Count('asset')).order_by('-total')[:10])
        for asset in assets:
            last_login = self.session_week.filter(asset=asset["asset"]).order_by('date_start').last()
            asset['last'] = last_login
        return assets

    def get_week_top10_user(self):
        users = list(self.session_week.values('user').annotate(
            total=Count('asset')).order_by('-total')[:10])
        for user in users:
            last_login = self.session_week.filter(user=user["user"]).order_by('date_start').last()
            user['last'] = last_login
        return users

    def get_last10_sessions(self):
        sessions = self.session_week.order_by('-date_start')[:10]
        for session in sessions:
            try:
                session.avatar_url = User.objects.get(username=session.user).avatar_url()
            except User.DoesNotExist:
                session.avatar_url = User.objects.first().avatar_url()
        return sessions

    def get_context_data(self, **kwargs):
        week_ago = timezone.now() - timezone.timedelta(weeks=1)
        month_ago = timezone.now() - timezone.timedelta(days=30)
        self.session_week = Session.objects.filter(date_start__gt=week_ago)
        self.session_month = Session.objects.filter(date_start__gt=month_ago)
        self.session_month_dates = self.session_month.dates('date_start', 'day')

        self.session_month_dates_archive = []
        time_min = datetime.datetime.min.time()
        time_max = datetime.datetime.max.time()

        for d in self.session_month_dates:
            ds = datetime.datetime.combine(d, time_min).replace(
                tzinfo=timezone.get_current_timezone())
            de = datetime.datetime.combine(d, time_max).replace(
                tzinfo=timezone.get_current_timezone())
            self.session_month_dates_archive.append(
                self.session_month.filter(date_start__range=(ds, de)))

        context = {
            'assets_count': self.get_asset_count(),
            'users_count': self.get_user_count(),
            'online_user_count': self.get_online_user_count(),
            'online_asset_count': self.get_online_session_count(),
            'user_visit_count_weekly': self.get_week_login_user_count(),
            'asset_visit_count_weekly': self.get_week_login_asset_count(),
            'user_visit_count_top_five': self.get_top5_user_a_week(),
            'month_str': self.get_month_day_metrics(),
            'month_total_visit_count': self.get_month_login_metrics(),
            'month_user': self.get_month_active_user_metrics(),
            'mouth_asset': self.get_month_active_asset_metrics(),
            'month_user_active': self.get_month_active_user_total(),
            'month_user_inactive': self.get_month_inactive_user_total(),
            'month_user_disabled': self.get_user_disabled_total(),
            'month_asset_active': self.get_month_active_asset_total(),
            'month_asset_inactive': self.get_month_inactive_asset_total(),
            'month_asset_disabled': self.get_asset_disabled_total(),
            'week_asset_hot_ten': self.get_week_top10_asset(),
            'last_login_ten': self.get_last10_sessions(),
            'week_user_hot_ten': self.get_week_top10_user(),
        }

        kwargs.update(context)
        return super(IndexView, self).get_context_data(**kwargs)


class LunaView(View):
    def get(self, request):
        msg = _("<div>Luna is a separately deployed program, you need to deploy Luna, coco, configure nginx for url distribution,</div> "
                "</div>If you see this page, prove that you are not accessing the nginx listening port. Good luck.</div>")
        return HttpResponse(msg)


class I18NView(View):
    def get(self, request, lang):
        referer_url = request.META.get('HTTP_REFERER', '/')
        response = HttpResponseRedirect(referer_url)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
        return response


api_url_pattern = re.compile(r'^/api/(?P<version>\w+)/(?P<app>\w+)/(?P<extra>.*)$')


class HttpResponseTemporaryRedirect(HttpResponse):
    status_code = 307

    def __init__(self, redirect_to):
        HttpResponse.__init__(self)
        self['Location'] = iri_to_uri(redirect_to)


@csrf_exempt
def redirect_format_api(request, *args, **kwargs):
    _path, query = request.path, request.GET.urlencode()
    matched = api_url_pattern.match(_path)
    if matched:
        version, app, extra = matched.groups()
        _path = '/api/{app}/{version}/{extra}?{query}'.format(**{
            "app": app, "version": version, "extra": extra,
            "query": query
        })
        return HttpResponseTemporaryRedirect(_path)
    else:
        return Response({"msg": "Redirect url failed: {}".format(_path)}, status=404)
