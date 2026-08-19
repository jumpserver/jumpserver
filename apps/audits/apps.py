from django.apps import AppConfig
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _


class AuditsConfig(AppConfig):
    name = 'audits'
    verbose_name = _('App Audits')

    def ready(self):
        from . import signal_handlers  # noqa
        from . import tasks  # noqa

        # 始终连接信号，是否发送 syslog 由 logging handler 根据
        # SYSLOG_ENABLE 开关动态决定，从而支持修改配置后立刻生效
        post_save.connect(signal_handlers.on_audits_log_create)
