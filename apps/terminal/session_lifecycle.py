from django.utils.translation import gettext_noop

from audits.const import ActivityChoices
from audits.models import ActivityLog
from common.utils import i18n_fmt
from terminal.models import Session


class SessionLifecycleEventBase(object):

    def __init__(self, session: Session, reason, *args, **kwargs):
        self.session = session
        self.reason = reason

    def detail(self):
        raise NotImplementedError

    def create_activity_log(self):
        log_obj = ActivityLog.objects.create(
            resource_id=self.session.id,
            type=ActivityChoices.session_log,
            detail=self.detail(),
            org_id=self.session.org_id
        )
        return log_obj


class AssetConnectSuccess(SessionLifecycleEventBase):
    name = "asset_connect_success"
    i18n_text = gettext_noop("Connect to asset %s success")

    def detail(self):
        return i18n_fmt(self.i18n_text, self.session.asset)


class AssetConnectFinished(SessionLifecycleEventBase):
    name = "asset_connect_finished"
    i18n_text = gettext_noop("Connect to asset %s finished: %s")

    def detail(self):
        asset = self.session.asset
        reason = self.reason
        return i18n_fmt(self.i18n_text, asset, reason)


class UserCreateShareLink(SessionLifecycleEventBase):
    name = "create_share_link"
    i18n_text = gettext_noop("User %s create share link")

    def detail(self):
        user = self.session.user
        return i18n_fmt(self.i18n_text, user)


class UserJoinSession(SessionLifecycleEventBase):
    name = "user_join_session"
    i18n_text = gettext_noop("User %s join session")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.get("user")

    def detail(self):
        return i18n_fmt(self.i18n_text, self.user)


class UserLeaveSession(SessionLifecycleEventBase):
    name = "user_leave_session"
    i18n_text = gettext_noop("User %s leave session")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.get("user")

    def detail(self):
        return i18n_fmt(self.i18n_text, self.user)


class AdminJoinMonitor(SessionLifecycleEventBase):
    name = "admin_join_monitor"
    i18n_text = gettext_noop("User %s join to monitor session")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.get("user")

    def detail(self):
        return i18n_fmt(self.i18n_text, self.user)


class AdminExitMonitor(SessionLifecycleEventBase):
    name = "admin_exit_monitor"
    i18n_text = gettext_noop("User %s exit to monitor session")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.get("user")

    def detail(self):
        return i18n_fmt(self.i18n_text, self.user)


class ReplayConvertStart(SessionLifecycleEventBase):
    name = "replay_convert_start"
    i18n_text = gettext_noop("Replay start to convert")

    def detail(self):
        return self.i18n_text


class ReplayConvertSuccess(SessionLifecycleEventBase):
    name = "replay_convert_success"
    i18n_text = gettext_noop("Replay successfully converted to MP4 format")

    def detail(self):
        return self.i18n_text


class ReplayConvertFailure(SessionLifecycleEventBase):
    name = "replay_convert_failure"
    i18n_text = gettext_noop("Replay failed to convert to MP4 format: %s")

    def detail(self):
        return i18n_fmt(self.i18n_text, self.reason)


class ReplayUploadStart(SessionLifecycleEventBase):
    name = "replay_upload_start"
    i18n_text = gettext_noop("Replay start to upload")

    def detail(self):
        return self.i18n_text


class ReplayUploadSuccess(SessionLifecycleEventBase):
    name = "replay_upload_success"
    i18n_text = gettext_noop("Replay successfully uploaded")

    def detail(self):
        return self.i18n_text


class ReplayUploadFailure(SessionLifecycleEventBase):
    name = "replay_upload_failure"
    i18n_text = gettext_noop("Replay failed to upload: %s")

    def detail(self):
        return i18n_fmt(self.i18n_text, self.reason)


reasons_map = {
    'connect_failed': gettext_noop('connect failed'),
    'connect_disconnect': gettext_noop('connection disconnect'),
    'user_close': gettext_noop('user closed'),
    'idle_disconnect': gettext_noop('idle disconnect'),
    'admin_terminate': gettext_noop('admin terminated'),
    'max_session_timeout': gettext_noop('maximum session time has been reached'),
    'permission_expired': gettext_noop('permission has expired'),
    'null_storage': gettext_noop('storage is null'),
}

lifecycle_events_map = {
    AssetConnectSuccess.name: AssetConnectSuccess,
    AssetConnectFinished.name: AssetConnectFinished,
    UserCreateShareLink.name: UserCreateShareLink,
    UserJoinSession.name: UserJoinSession,
    UserLeaveSession.name: UserLeaveSession,
    AdminJoinMonitor.name: AdminJoinMonitor,
    AdminExitMonitor.name: AdminExitMonitor,
    ReplayConvertStart.name: ReplayConvertStart,
    ReplayConvertSuccess.name: ReplayConvertSuccess,
    ReplayConvertFailure.name: ReplayConvertFailure,
    ReplayUploadStart.name: ReplayUploadStart,
    ReplayUploadSuccess.name: ReplayUploadSuccess,
    ReplayUploadFailure.name: ReplayUploadFailure,
}
