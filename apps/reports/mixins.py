from django.utils import timezone
from rest_framework.request import Request

from common.utils import lazyproperty
from common.utils.timezone import local_zero_hour, local_now


class DateRangeMixin:
    request: Request
    days_param = 'days'
    default_days = 1

    @lazyproperty
    def days(self) -> int:
        raw = self.request.query_params.get(self.days_param, self.default_days)
        try:
            return int(raw)
        except (ValueError, TypeError):
            return self.default_days

    @property
    def start_datetime(self):
        if self.days == 1:
            return local_zero_hour()
        return local_now() - timezone.timedelta(days=self.days)

    @property
    def date_range_bounds(self) -> tuple:
        start = self.start_datetime.date()
        end = (local_now() + timezone.timedelta(days=1)).date()
        return start, end

    @lazyproperty
    def date_range_list(self) -> list:
        return [
            (local_now() - timezone.timedelta(days=i)).date()
            for i in range(self.days - 1, -1, -1)
        ]

    def filter_by_date_range(self, queryset, field_name: str):
        start, end = self.date_range_bounds
        return queryset.filter(**{f'{field_name}__range': (start, end)})

    @lazyproperty
    def dates_metrics_date(self):
        return [date.strftime('%m-%d') for date in self.date_range_list] or ['0']
