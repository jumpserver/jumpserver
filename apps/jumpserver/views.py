from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from users.models import User
from assets.models import Asset
from audits.models import ProxyLog


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = 'index.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('assets:user-asset-list')
        return super(IndexView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        month_ago = timezone.now() - timezone.timedelta(days=30)
        proxy_log_seven_days = ProxyLog.objects.filter(date_start__gt=seven_days_ago, is_failed=False)
        proxy_log_month = ProxyLog.objects.filter(date_start__gt=month_ago, is_failed=False)
        month_dates = proxy_log_month.dates('date_start', 'day')
        month_total_visit = [ProxyLog.objects.filter(date_start__date=d) for d in month_dates]
        month_str = [d.strftime('%m-%d') for d in month_dates] or ['0']
        month_total_visit_count = [p.count() for p in month_total_visit] or [0]
        month_user = [p.values('user').distinct().count() for p in month_total_visit] or [0]
        month_asset = [p.values('asset').distinct().count() for p in month_total_visit] or [0]
        month_user_active = User.objects.filter(last_login__gt=month_ago).count()
        month_user_inactive = User.objects.filter(last_login__lt=month_ago).count()
        month_user_disabled = User.objects.filter(is_active=False).count()
        month_asset_active = proxy_log_month.values('asset').distinct().count()
        month_asset_inactive = Asset.objects.all().count() - month_asset_active
        month_asset_disabled = Asset.objects.filter(is_active=False).count()
        week_asset_hot_ten = list(proxy_log_seven_days.values('asset').annotate(total=Count('asset')).order_by('-total')[:10])
        for p in week_asset_hot_ten:
            last_login = ProxyLog.objects.filter(asset=p['asset']).order_by('date_start').last()
            p['last'] = last_login
        last_login_ten = ProxyLog.objects.all().order_by('-date_start')[:10]
        for p in last_login_ten:
            try:
                p.avatar_url = User.objects.get(username=p.user).avatar_url()
            except User.DoesNotExist:
                p.avatar_url = User.objects.first().avatar_url()
        week_user_hot_ten = list(proxy_log_seven_days.values('user').annotate(total=Count('user')).order_by('-total')[:10])
        for p in week_user_hot_ten:
            last_login = ProxyLog.objects.filter(user=p['user']).order_by('date_start').last()
            p['last'] = last_login

        context = {
            'assets_count': Asset.objects.count(),
            'users_count': User.objects.filter(role__in=('Admin', 'User')).count(),
            'online_user_count': ProxyLog.objects.filter(is_finished=False).values('user').distinct().count(),
            'online_asset_count': ProxyLog.objects.filter(is_finished=False).values('asset').distinct().count(),
            'user_visit_count_weekly': proxy_log_seven_days.values('user').distinct().count(),
            'asset_visit_count_weekly': proxy_log_seven_days.count(),
            'user_visit_count_top_five': proxy_log_seven_days.values('user').annotate(total=Count('user')).order_by('-total')[:5],
            'month_str': month_str,
            'month_total_visit_count': month_total_visit_count,
            'month_user': month_user,
            'mouth_asset': month_asset,
            'month_user_active': month_user_active,
            'month_user_inactive': month_user_inactive,
            'month_user_disabled': month_user_disabled,
            'month_asset_active': month_asset_active,
            'month_asset_inactive': month_asset_inactive,
            'month_asset_disabled': month_asset_disabled,
            'week_asset_hot_ten': week_asset_hot_ten,
            'last_login_ten': last_login_ten,
            'week_user_hot_ten': week_user_hot_ten,
        }

        kwargs.update(context)
        return super(IndexView, self).get_context_data(**kwargs)
