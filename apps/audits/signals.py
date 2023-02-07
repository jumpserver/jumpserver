from django.dispatch import Signal


post_activity_log = Signal(
    providing_args=('resource_id', 'detail', 'detail_url')
)
