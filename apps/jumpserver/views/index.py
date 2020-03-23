from django.core.cache import cache
from django.views.generic import TemplateView
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db.models import Count, Max
from django.shortcuts import redirect

from users.models import User
from assets.models import Asset
from terminal.models import Session
from orgs.utils import current_org
from common.permissions import PermissionsMixin, IsValidUser
from common.utils import timeit, lazyproperty

__all__ = ['IndexView']


class MonthLoginMetricMixin:
    @lazyproperty
    def session_month(self):
        month_ago = timezone.now() - timezone.timedelta(days=30)
        session_month = Session.objects.filter(date_start__gt=month_ago)
        return session_month

    @lazyproperty
    def session_month_dates(self):
        dates = self.session_month.dates('date_start', 'day')
        return dates

    def get_month_day_metrics(self):
        month_str = [
            d.strftime('%m-%d') for d in self.session_month_dates
        ] or ['0']
        return month_str

    @staticmethod
    def get_cache_key(date, tp):
        date_str = date.strftime("%Y%m%d")
        key = "SESSION_MONTH_{}_{}".format(tp, date_str)
        return key

    def __get_data_from_cache(self, date, tp):
        if date == timezone.now().date():
            return None
        cache_key = self.get_cache_key(date, tp)
        count = cache.get(cache_key)
        return count

    def __set_data_to_cache(self, date, tp, count):
        cache_key = self.get_cache_key(date, tp)
        cache.set(cache_key, count, 3600*24*7)

    @lazyproperty
    def user_disabled_total(self):
        return current_org.get_org_members().filter(is_active=False).count()

    @lazyproperty
    def asset_disabled_total(self):
        return Asset.objects.filter(is_active=False).count()

    @staticmethod
    def get_date_start_2_end(d):
        time_min = timezone.datetime.min.time()
        time_max = timezone.datetime.max.time()
        tz = timezone.get_current_timezone()
        ds = timezone.datetime.combine(d, time_min).replace(tzinfo=tz)
        de = timezone.datetime.combine(d, time_max).replace(tzinfo=tz)
        return ds, de

    def get_date_login_count(self, date):
        tp = "LOGIN"
        count = self.__get_data_from_cache(date, tp)
        if count is not None:
            return count
        ds, de = self.get_date_start_2_end(date)
        count = Session.objects.filter(date_start__range=(ds, de)).count()
        self.__set_data_to_cache(date, tp, count)
        return count

    def get_month_login_metrics(self):
        data = []
        for d in self.session_month_dates:
            count = self.get_date_login_count(d)
            data.append(count)
        if len(data) == 0:
            data = [0]
        return data

    def get_date_user_count(self, date):
        tp = "USER"
        count = self.__get_data_from_cache(date, tp)
        if count is not None:
            return count
        ds, de = self.get_date_start_2_end(date)
        count = Session.objects.filter(date_start__range=(ds, de))\
            .values('user').distinct().count()
        self.__set_data_to_cache(date, tp, count)
        return count

    def get_month_active_user_metrics(self):
        data = []
        for d in self.session_month_dates:
            count = self.get_date_user_count(d)
            data.append(count)
        return data

    def get_date_asset_count(self, date):
        tp = "ASSET"
        count = self.__get_data_from_cache(date, tp)
        if count is not None:
            return count
        ds, de = self.get_date_start_2_end(date)
        count = Session.objects.filter(date_start__range=(ds, de)) \
            .values('asset').distinct().count()
        self.__set_data_to_cache(date, tp, count)
        return count

    def get_month_active_asset_metrics(self):
        data = []
        for d in self.session_month_dates:
            count = self.get_date_asset_count(d)
            data.append(count)
        return data

    @lazyproperty
    def month_active_user_total(self):
        count = self.session_month.values('user').distinct().count()
        return count

    @lazyproperty
    def month_inactive_user_total(self):
        total = current_org.get_org_members().count()
        active = self.month_active_user_total
        count = total - active
        if count < 0:
            count = 0
        return count

    @lazyproperty
    def month_active_asset_total(self):
        return self.session_month.values('asset').distinct().count()

    @lazyproperty
    def month_inactive_asset_total(self):
        total = Asset.objects.all().count()
        active = self.month_active_asset_total
        count = total - active
        if count < 0:
            count = 0
        return count

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'month_str': self.get_month_day_metrics(),
            'month_total_visit_count': self.get_month_login_metrics(),
            'month_user': self.get_month_active_user_metrics(),
            'mouth_asset': self.get_month_active_asset_metrics(),
            'month_user_active': self.month_active_user_total,
            'month_user_inactive': self.month_inactive_user_total,
            'month_user_disabled': self.user_disabled_total,
            'month_asset_active': self.month_active_asset_total,
            'month_asset_inactive': self.month_inactive_asset_total,
            'month_asset_disabled': self.asset_disabled_total,
        })
        return context


class WeekSessionMetricMixin:
    session_week = None

    @lazyproperty
    def session_week(self):
        week_ago = timezone.now() - timezone.timedelta(weeks=1)
        session_week = Session.objects.filter(date_start__gt=week_ago)
        return session_week

    def get_top5_user_a_week(self):
        users = self.session_week.values('user') \
                    .annotate(total=Count('user')) \
                    .order_by('-total')[:5]
        return users

    def get_week_login_user_count(self):
        return self.session_week.values('user').distinct().count()

    def get_week_login_asset_count(self):
        return self.session_week.count()

    def get_week_top10_assets(self):
        assets = self.session_week.values("asset")\
            .annotate(total=Count("asset"))\
            .annotate(last=Max("date_start")).order_by("-total")[:10]
        return assets

    def get_week_top10_users(self):
        users = self.session_week.values("user") \
                     .annotate(total=Count("user")) \
                     .annotate(last=Max("date_start")).order_by("-total")[:10]
        return users

    def get_last10_sessions(self):
        sessions = self.session_week.order_by('-date_start')[:10]
        for session in sessions:
            session.avatar_url = User.get_avatar_url("")
        return sessions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user_visit_count_weekly': self.get_week_login_user_count(),
            'asset_visit_count_weekly': self.get_week_login_asset_count(),
            'user_visit_count_top_five': self.get_top5_user_a_week(),
            'last_login_ten': self.get_last10_sessions(),
            'week_asset_hot_ten': self.get_week_top10_assets(),
            'week_user_hot_ten': self.get_week_top10_users(),
        })
        return context


class IndexView(PermissionsMixin, MonthLoginMetricMixin, WeekSessionMetricMixin, TemplateView):
    template_name = 'index.html'
    permission_classes = [IsValidUser]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_common_user:
            return redirect('assets:user-asset-list')
        return super(IndexView, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def get_user_count():
        return current_org.get_org_members().count()

    @staticmethod
    def get_asset_count():
        return Asset.objects.all().count()

    @staticmethod
    def get_online_user_count():
        count = Session.objects.filter(is_finished=False)\
            .values_list('user', flat=True).distinct().count()
        return count

    @staticmethod
    def get_online_session_count():
        return Session.objects.filter(is_finished=False).count()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'assets_count': self.get_asset_count(),
            'users_count': self.get_user_count(),
            'online_user_count': self.get_online_user_count(),
            'online_asset_count': self.get_online_session_count(),
            'app': _("Dashboard"),
        })
        return context
