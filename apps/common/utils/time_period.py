from common.utils.timezone import local_now


def contains_time_period(time_periods, ctime=None):
    """
    time_periods: [{"id": 1, "value": "00:00~07:30、10:00~13:00"}, {"id": 2, "value": "00:00~00:00"}]
    """
    if not time_periods:
        return None

    if ctime is None:
        ctime = local_now()
    current_time = ctime.strftime('%H:%M')
    today_time_period = next(filter(lambda x: str(x['id']) == local_now().strftime("%w"), time_periods))
    today_time_period = today_time_period['value']
    if not today_time_period:
        return False

    for time in today_time_period.split('、'):
        start, end = time.split('~')
        end = "24:00" if end == "00:00" else end
        if start <= current_time <= end:
            return True
    return False
