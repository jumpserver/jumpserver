import datetime

from django.http import HttpResponse
from django.views.generic import TemplateView, View
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from users.models import User
from assets.models import Asset
from terminal.models import Session


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    session_week = None
    session_month = None
    session_month_dates = []
    session_month_dates_archive = []

    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('assets:user-asset-list')
        return super(IndexView, self).get(request, *args, **kwargs)

    @staticmethod
    def get_user_count():
        return User.objects.filter(role__in=('Admin', 'User')).count()

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
        # return self.session_week.values('asset').distinct().count()

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
        return User.objects.all().count() - self.get_month_active_user_total()

    def get_month_active_asset_total(self):
        return self.session_month.values('asset').distinct().count()

    def get_month_inactive_asset_total(self):
        return Asset.objects.all().count() - self.get_month_active_asset_total()

    @staticmethod
    def get_user_disabled_total():
        return User.objects.filter(is_active=False).count()

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
        msg = """
        Luna是单独部署的一个程序，你需要部署luna，coco，配置nginx做url分发, 
        如果你看到了这个页面，证明你访问的不是nginx监听的端口，祝你好运
        """
        return HttpResponse(msg)