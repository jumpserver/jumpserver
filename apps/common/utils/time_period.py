from common.utils.timezone import now


def contains_time_period(time_periods):
    """
    time_periods: [{"id": 1, "value": "00:00~07:30、10:00~13:00"}, {"id": 2, "value": "00:00~00:00"}]
    """
    if not time_periods:
        return False

    current_time = now().strftime('%H:%M')
    today_time_period = next(filter(lambda x: str(x['id']) == now().strftime("%w"), time_periods))
    for time in today_time_period['value'].split('、'):
        start, end = time.split('~')
        end = "24:00" if end == "00:00" else end
        if start <= current_time <= end:
            return True
    return False
