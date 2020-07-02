import os

from django.core.cache import cache
from django.utils import timezone
from django.utils.timesince import timesince
from django.db.models import Count, Max
from django.http.response import JsonResponse, FileResponse
from django.conf import settings
from rest_framework.views import APIView
from collections import Counter
from pyecharts.charts import Line
from pyecharts import options as opts
from pyecharts.charts import Bar, Page
from pyecharts.render import make_snapshot
from snapshot_phantomjs import snapshot

from users.models import User
from assets.models import Asset
from terminal.models import Session
from orgs.utils import current_org
from common.permissions import IsOrgAdmin
from common.utils import lazyproperty

__all__ = ['IndexApi']


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

    def get_month_metrics_date(self):
        month_metrics_date = [d.strftime('%m-%d') for d in self.session_month_dates] or ['0']
        return month_metrics_date

    @staticmethod
    def get_cache_key(date, tp):
        date_str = date.strftime("%Y%m%d")
        key = "SESSION_MONTH_{}_{}_{}".format(current_org.id, tp, date_str)
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

    def get_month_metrics_total_count_login(self):
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
        count = len(set(Session.objects.filter(date_start__range=(ds, de)).values_list('user', flat=True)))
        self.__set_data_to_cache(date, tp, count)
        return count

    def get_month_metrics_total_count_active_users(self):
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
        count = len(set(Session.objects.filter(date_start__range=(ds, de)).values_list('asset', flat=True)))
        self.__set_data_to_cache(date, tp, count)
        return count

    def get_month_metrics_total_count_active_assets(self):
        data = []
        for d in self.session_month_dates:
            count = self.get_date_asset_count(d)
            data.append(count)
        return data

    @lazyproperty
    def month_total_count_active_users(self):
        count = len(set(self.session_month.values_list('user', flat=True)))
        return count

    @lazyproperty
    def month_total_count_inactive_users(self):
        total = current_org.get_org_members().count()
        active = self.month_total_count_active_users
        count = total - active
        if count < 0:
            count = 0
        return count

    @lazyproperty
    def month_total_count_disabled_users(self):
        return current_org.get_org_members().filter(is_active=False).count()

    @lazyproperty
    def month_total_count_active_assets(self):
        return len(set(self.session_month.values_list('asset', flat=True)))

    @lazyproperty
    def month_total_count_inactive_assets(self):
        total = Asset.objects.all().count()
        active = self.month_total_count_active_assets
        count = total - active
        if count < 0:
            count = 0
        return count

    @lazyproperty
    def month_total_count_disabled_assets(self):
        return Asset.objects.filter(is_active=False).count()


class WeekSessionMetricMixin:
    session_week = None

    @lazyproperty
    def session_week(self):
        week_ago = timezone.now() - timezone.timedelta(weeks=1)
        session_week = Session.objects.filter(date_start__gt=week_ago)
        return session_week

    def get_week_login_times_top5_users(self):
        users = self.session_week.values_list('user', flat=True)
        users = [
            {'user': user, 'total': total}
            for user, total in Counter(users).most_common(5)
        ]
        return users

    def get_week_total_count_login_users(self):
        return len(set(self.session_week.values_list('user', flat=True)))

    def get_week_total_count_login_times(self):
        return self.session_week.count()

    def get_week_login_times_top10_assets(self):
        assets = self.session_week.values("asset")\
            .annotate(total=Count("asset"))\
            .annotate(last=Max("date_start")).order_by("-total")[:10]
        for asset in assets:
            asset['last'] = str(asset['last'])
        return list(assets)

    def get_week_login_times_top10_users(self):
        users = self.session_week.values("user") \
                     .annotate(total=Count("user")) \
                     .annotate(last=Max("date_start")).order_by("-total")[:10]
        for user in users:
            user['last'] = str(user['last'])
        return list(users)

    def get_week_login_record_top10_sessions(self):
        sessions = self.session_week.order_by('-date_start')[:10]
        for session in sessions:
            session.avatar_url = User.get_avatar_url("")
        sessions = [
            {
                'user': session.user,
                'asset': session.asset,
                'is_finished': session.is_finished,
                'date_start': str(session.date_start),
                'timesince': timesince(session.date_start)
            }
            for session in sessions
        ]
        return sessions


class TotalCountMixin:
    @staticmethod
    def get_total_count_users():
        return current_org.get_org_members().count()

    @staticmethod
    def get_total_count_assets():
        return Asset.objects.all().count()

    @staticmethod
    def get_total_count_online_users():
        count = len(set(Session.objects.filter(is_finished=False).values_list('user', flat=True)))
        return count

    @staticmethod
    def get_total_count_online_sessions():
        return Session.objects.filter(is_finished=False).count()


class IndexApi(TotalCountMixin, WeekSessionMetricMixin, MonthLoginMetricMixin, APIView):
    permission_classes = (IsOrgAdmin,)
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        data = {}

        query_params = self.request.query_params

        _all = query_params.get('all')

        if _all or query_params.get('total_count'):
            data.update({
                'total_count_assets': self.get_total_count_assets(),
                'total_count_users': self.get_total_count_users(),
                'total_count_online_users': self.get_total_count_online_users(),
                'total_count_online_sessions': self.get_total_count_online_sessions(),
            })

        if _all or query_params.get('month_metrics'):
            data.update({
                'month_metrics_date': self.get_month_metrics_date(),
                'month_metrics_total_count_login': self.get_month_metrics_total_count_login(),
                'month_metrics_total_count_active_users': self.get_month_metrics_total_count_active_users(),
                'month_metrics_total_count_active_assets': self.get_month_metrics_total_count_active_assets(),
            })

        if _all or query_params.get('month_total_count_users'):
            data.update({
                'month_total_count_active_users': self.month_total_count_active_users,
                'month_total_count_inactive_users': self.month_total_count_inactive_users,
                'month_total_count_disabled_users': self.month_total_count_disabled_users,
            })

        if _all or query_params.get('month_total_count_assets'):
            data.update({
                'month_total_count_active_assets': self.month_total_count_active_assets,
                'month_total_count_inactive_assets': self.month_total_count_inactive_assets,
                'month_total_count_disabled_assets': self.month_total_count_disabled_assets,
            })

        if _all or query_params.get('week_total_count'):
            data.update({
                'week_total_count_login_users': self.get_week_total_count_login_users(),
                'week_total_count_login_times': self.get_week_total_count_login_times(),
            })

        if _all or query_params.get('week_login_times_top5_users'):
            data.update({
                'week_login_times_top5_users': self.get_week_login_times_top5_users(),
            })

        if _all or query_params.get('week_login_times_top10_assets'):
            data.update({
                'week_login_times_top10_assets': self.get_week_login_times_top10_assets(),
            })

        if _all or query_params.get('week_login_times_top10_users'):
            data.update({
                'week_login_times_top10_users': self.get_week_login_times_top10_users(),
            })

        if _all or query_params.get('week_login_record_top10_sessions'):
            data.update({
                'week_login_record_top10_sessions': self.get_week_login_record_top10_sessions()
            })

        return JsonResponse(data, status=200)


class ExportIndexApi(TotalCountMixin, WeekSessionMetricMixin, MonthLoginMetricMixin, APIView):
    permission_classes = (IsOrgAdmin,)
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        month_metrics_date = self.get_month_metrics_date()
        month_metrics_total_count_login = self.get_month_metrics_total_count_login()
        month_metrics_total_count_active_users = self.get_month_metrics_total_count_active_users()
        month_metrics_total_count_active_assets = self.get_month_metrics_total_count_active_assets()

        c1 = (
            Line()
                .add_xaxis(month_metrics_date)
                .add_yaxis("登录次数", month_metrics_total_count_login, is_smooth=True)
                .add_yaxis("活跃用户", month_metrics_total_count_active_users, is_smooth=True)
                .add_yaxis("活跃资产", month_metrics_total_count_active_assets, is_smooth=True)
                .set_series_opts(
                areastyle_opts=opts.AreaStyleOpts(opacity=1),
                label_opts=opts.LabelOpts(is_show=False),
            )
                .set_global_opts(
                title_opts=opts.TitleOpts(title="会话统计"),
                xaxis_opts=opts.AxisOpts(
                    axistick_opts=opts.AxisTickOpts(is_align_with_label=True),
                    is_scale=False,
                    boundary_gap=False,
                    offset=1,
                ),
            )
                # .render("line_areastyle_boundary_gap.html")
        )

        total_count_assets = self.get_total_count_assets()
        total_count_users = self.get_total_count_users()
        total_count_online_users = self.get_total_count_online_users()
        total_count_online_sessions = self.get_total_count_online_sessions()

        c2 = (
            Bar()
                .add_xaxis(
                [
                    "用户总数",
                    "资产总数",
                    "在线用户",
                    "在线会话",
                ]
            )
                .add_yaxis("", [total_count_users, total_count_assets, total_count_online_users, total_count_online_sessions])
                .set_global_opts(
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-15), offset=1),
                title_opts=opts.TitleOpts(title="概览", subtitle=""),
            )
                # .render("bar_rotate_xaxis_label.html")
        )

        week_login_times_top10_users = self.get_week_login_times_top10_users()
        x, y = zip(*[(item['user'], item['total']) for item in week_login_times_top10_users])
        c3 = (
            Bar()
                .add_xaxis(x)
                .add_yaxis("", y)
                .set_global_opts(
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-15), offset=1),
                title_opts=opts.TitleOpts(title="周用户 TOP10", subtitle=""),
            )
        )

        week_login_times_top10_assets = self.get_week_login_times_top10_assets()
        x, y = zip(*[(item['asset'], item['total']) for item in week_login_times_top10_assets])
        c4 = (
            Bar()
                .add_xaxis(x)
                .add_yaxis("", y)
                .set_global_opts(
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-15), offset=1),
                title_opts=opts.TitleOpts(title="周资产 TOP10", subtitle=""),
            )
        )

        path = os.path.join(os.path.dirname(settings.BASE_DIR), 'tmp', 'export_index.html')

        page = Page()
        page.add(c1, c2, c3, c4)
        page.render(path)

        response = FileResponse(open(path, mode='rb'))
        response['Content-Type'] = 'application/octet-stream'
        disposition = "attachment; filename*=UTF-8''{}".format('export_index.html')
        response["Content-Disposition"] = disposition
        return response
