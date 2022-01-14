import os
import time
import pandas as pd
from collections import defaultdict, OrderedDict

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.models import AuthBook
from assets.api import AccountViewSet
from assets.serializers import AccountSecretSerializer
from assets.notifications import AccountBackupExecutionTaskMsg
from applications.api import ApplicationAccountViewSet
from applications.const import AppType
from applications.serializers import AppAccountSecretSerializer
from users.models import User
from common.utils import get_logger
from common.utils.timezone import local_now_display
from common.utils.file import encrypt_and_compress_zip_file

logger = get_logger(__file__)

PATH = os.path.join(os.path.dirname(settings.BASE_DIR), 'tmp')


class BaseAccountHandler:
    @classmethod
    def unpack_data(cls, serializer_data, data=None):
        if data is None:
            data = {}
        for k, v in serializer_data.items():
            if isinstance(v, OrderedDict):
                cls.unpack_data(v, data)
            else:
                data[k] = v
        return data

    @classmethod
    def get_header_backup_fields(cls, serializer, fields=None, fields_backup=None):
        if fields_backup is None:
            fields_backup = []
        if fields is None:
            fields = {}
        try:
            backup = serializer.Meta.fields_backup
        except AttributeError:
            backup = serializer.fields.keys()

        for field in backup:
            fields_backup.append(field)

        for k, v in serializer.fields.items():
            if isinstance(v, serializers.Serializer):
                cls.get_header_backup_fields(v, fields, fields_backup)
            else:
                fields[k] = v.label
        return fields, fields_backup

    @classmethod
    def create_row(cls, account, serializer):
        serializer = serializer(account)
        data = cls.unpack_data(serializer.data)
        header, fields_backup = cls.get_header_backup_fields(serializer)
        row = {}
        fields_backup = fields_backup + [
            'username', 'password', 'private_key', 'public_key',
            'date_created', 'date_updated', 'version'
        ]
        for field in fields_backup:
            row[header[field]] = data[field]
        return row


class AssetAccountHandler(BaseAccountHandler):
    @staticmethod
    def get_filename(plan_name):
        filename = os.path.join(
            PATH, f'{plan_name}-{_("Asset")}-{local_now_display()}-{time.time()}.xlsx'
        )
        return filename

    @classmethod
    def create_df(cls):
        df_dict = defaultdict(list)
        label_key = AuthBook._meta.verbose_name
        accounts = AccountViewSet().get_queryset()
        for account in accounts:
            account.load_auth()
            row = cls.create_row(account, AccountSecretSerializer)
            df_dict[label_key].append(row)
        for k, v in df_dict.items():
            df_dict[k] = pd.DataFrame(v)
        logger.info(
            '\n\033[33m- 共收集{}条资产账号\033[0m'.format(accounts.count())
        )
        return df_dict


class AppAccountHandler(BaseAccountHandler):
    @staticmethod
    def get_filename(plan_name):
        filename = os.path.join(
            PATH, f'{plan_name}-{_("Application")}-{local_now_display()}-{time.time()}.xlsx'
        )
        return filename

    @classmethod
    def create_df(cls):
        df_dict = defaultdict(list)
        accounts = ApplicationAccountViewSet().get_queryset()
        for account in accounts:
            account.load_auth()
            app_type = account.app.type
            if app_type == 'postgresql':
                label_key = getattr(AppType, 'pgsql').label
            else:
                label_key = getattr(AppType, app_type).label
            row = cls.create_row(account, AppAccountSecretSerializer)
            df_dict[label_key].append(row)
        for k, v in df_dict.items():
            df_dict[k] = pd.DataFrame(v)
        logger.info(
            '\n\033[33m- 共收集{}条应用账号\033[0m'.format(accounts.count())
        )
        return df_dict


HANDLER_MAP = {
    'asset': AssetAccountHandler,
    'application': AppAccountHandler
}


class AccountBackupHandler:
    def __init__(self, execution):
        self.execution = execution
        self.plan_name = self.execution.plan.name
        self.is_frozen = False  # 任务状态冻结标志

    def create_excel(self):
        logger.info(
            '\n'
            '\033[32m>>> 正在生成资产或应用相关备份信息文件\033[0m'
            ''
        )
        # Print task start date
        time_start = time.time()
        info = {}
        for account_type in self.execution.types:
            if account_type in HANDLER_MAP:
                account_handler = HANDLER_MAP[account_type]
                df = account_handler.create_df()
                filename = account_handler.get_filename(self.plan_name)
                info[filename] = df
        for filename, df_dict in info.items():
            with pd.ExcelWriter(filename) as w:
                for sheet, df in df_dict.items():
                    sheet = sheet.replace(' ', '-')
                    getattr(df, 'to_excel')(w, sheet_name=sheet, index=False)
        timedelta = round((time.time() - time_start), 2)
        logger.info('步骤完成: 用时 {}s'.format(timedelta))
        return list(info.keys())

    def send_backup_mail(self, files):
        recipients = self.execution.plan_snapshot.get('recipients')
        if not recipients:
            return
        recipients = User.objects.filter(id__in=list(recipients))
        logger.info(
            '\n'
            '\033[32m>>> 发送备份邮件\033[0m'
            ''
        )
        plan_name = self.plan_name
        for user in recipients:
            if not user.secret_key:
                attachment_list = []
            else:
                password = user.secret_key.encode('utf8')
                attachment = os.path.join(PATH, f'{plan_name}-{local_now_display()}-{time.time()}.zip')
                encrypt_and_compress_zip_file(attachment, password, files)
                attachment_list = [attachment, ]
            AccountBackupExecutionTaskMsg(plan_name, user).publish(attachment_list)
            logger.info('邮件已发送至{}({})'.format(user, user.email))
        for file in files:
            os.remove(file)

    def step_perform_task_update(self, is_success, reason):
        self.execution.reason = reason[:1024]
        self.execution.is_success = is_success
        self.execution.save()
        logger.info('已完成对任务状态的更新')

    def step_finished(self, is_success):
        if is_success:
            logger.info('任务执行成功')
        else:
            logger.error('任务执行失败')

    def _run(self):
        is_success = False
        error = '-'
        try:
            files = self.create_excel()
            self.send_backup_mail(files)
        except Exception as e:
            self.is_frozen = True
            logger.error('任务执行被异常中断')
            logger.info('下面打印发生异常的 Traceback 信息 : ')
            logger.error(e, exc_info=True)
            error = str(e)
        else:
            is_success = True
        finally:
            reason = error
            self.step_perform_task_update(is_success, reason)
            self.step_finished(is_success)

    def run(self):
        logger.info('任务开始: {}'.format(local_now_display()))
        time_start = time.time()
        try:
            self._run()
        except Exception as e:
            logger.error('任务运行出现异常')
            logger.error('下面显示异常 Traceback 信息: ')
            logger.error(e, exc_info=True)
        finally:
            logger.info('\n任务结束: {}'.format(local_now_display()))
            timedelta = round((time.time() - time_start), 2)
            logger.info('用时: {}'.format(timedelta))
