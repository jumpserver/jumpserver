from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from premailer import transform

from accounts.models import ChangeSecretRecord
from common.tasks import send_mail_attachment_async, upload_backup_to_obj_storage
from notifications.notifications import UserMessage
from terminal.models.component.storage import ReplayStorage
from users.models import User


class AccountBackupExecutionTaskMsg:
    subject = _('Notification of account backup route task results')

    def __init__(self, name: str, user: User):
        self.name = name
        self.user = user

    @property
    def message(self):
        name = self.name
        if self.user.secret_key:
            return _('{} - The account backup passage task has been completed.'
                     ' See the attachment for details').format(name)
        else:
            return _("{} - The account backup passage task has been completed: "
                     "the encryption password has not been set - "
                     "please go to personal information -> Basic file encryption password for preference settings"
                     ).format(name)

    def publish(self, attachment_list=None):
        send_mail_attachment_async(
            self.subject, self.message, [self.user.email], attachment_list
        )


class AccountBackupByObjStorageExecutionTaskMsg:
    subject = _('Notification of account backup route task results')

    def __init__(self, name: str, obj_storage: ReplayStorage):
        self.name = name
        self.obj_storage = obj_storage

    @property
    def message(self):
        name = self.name
        return _('{} - The account backup passage task has been completed.'
                 ' See the attachment for details').format(name)

    def publish(self, attachment_list=None):
        upload_backup_to_obj_storage(
            self.obj_storage, attachment_list
        )


class ChangeSecretExecutionTaskMsg:
    subject = _('Notification of implementation result of encryption change plan')

    def __init__(self, name: str, user: User, summary):
        self.name = name
        self.user = user
        self.summary = summary

    @property
    def message(self):
        name = self.name
        if self.user.secret_key:
            default_message = _('{} - The encryption change task has been completed. '
                                'See the attachment for details').format(name)

        else:
            default_message = _("{} - The encryption change task has been completed: the encryption "
                                "password has not been set - please go to personal information -> "
                                "set encryption password in preferences").format(name)
        return self.summary + '\n' + default_message

    def publish(self, attachments=None):
        send_mail_attachment_async(
            self.subject, self.message, [self.user.email], attachments
        )


class GatherAccountChangeMsg(UserMessage):
    subject = _('Gather account change information')

    def __init__(self, user, change_info: dict):
        self.change_info = change_info
        super().__init__(user)

    def get_html_msg(self) -> dict:
        context = {'change_info': self.change_info}
        message = render_to_string('accounts/asset_account_change_info.html', context)

        return {
            'subject': str(self.subject),
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        user = User.objects.first()
        return cls(user, {})


class ChangeSecretReportMsg(UserMessage):
    subject = _('Change secret or push account failed information')

    def __init__(self, user, context: dict):
        self.context = context
        super().__init__(user)

    def get_html_msg(self) -> dict:
        report = render_to_string(
            'accounts/change_secret_report.html',
            self.context
        )
        message = transform(report)
        return {
            'subject': str(self.subject),
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        name = 'test'
        user = User.objects.first()
        record = ChangeSecretRecord.objects.first()
        execution_id = str(record.execution_id)
        return cls(user, {})
