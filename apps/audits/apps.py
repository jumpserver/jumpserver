from django.apps import AppConfig, apps
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save

from .const import MODELS_NEED_RECORD


class AuditsConfig(AppConfig):
    name = 'audits'
    verbose_name = _('Audits')

    def _set_operate_log_monitor_models(self):
        exclude_label = {
            'audits', 'django_cas_ng', 'captcha', 'admin',
            'django_celery_beat', 'contenttypes', 'sessions',
            'jms_oidc_rp', 'auth'
        }
        exclude_object_name = {
            'UserPasswordHistory', 'ContentType',
            'SiteMessage', 'SiteMessageUsers',
            'PlatformAutomation', 'PlatformProtocol', 'Protocol',
            'HistoricalAccount', 'GatheredUser', 'ApprovalRule',
            'BaseAutomation', 'ChangeSecretRecord', 'CeleryTask',
            'Command', 'JobAuditLog',
            'ConnectionToken', 'Session', 'SessionJoinRecord',
            'HistoricalJob', 'Status', 'TicketStep', 'Ticket',
            'UserAssetGrantedTreeNodeRelation', 'TicketAssignee',
            'SuperTicket', 'SuperConnectionToken', 'PermNode',
            'PermedAsset', 'PermedAccount', 'MenuPermission',
            'Permission', 'TicketSession', 'ApplyLoginTicket',
            'ApplyCommandTicket', 'ApplyLoginAssetTicket',
            ''

        }
        for i, app in enumerate(apps.get_models(), 1):
            app_label = app._meta.app_label
            app_object_name = app._meta.object_name
            if app_label in exclude_label or \
                    app_object_name in exclude_object_name or \
                    app_object_name.endswith('Execution'):
                continue
            MODELS_NEED_RECORD.append(app_object_name)

    def ready(self):
        from . import signal_handlers
        if settings.SYSLOG_ENABLE:
            post_save.connect(signal_handlers.on_audits_log_create)

        self._set_operate_log_monitor_models()
