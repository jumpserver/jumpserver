from django.dispatch import Signal

category_setting_updated = Signal(providing_args=('category', 'serializer'))
