from django.dispatch import Signal

post_user_create = Signal()
post_user_change_password = Signal()
pre_user_leave_org = Signal()
post_user_leave_org = Signal()
