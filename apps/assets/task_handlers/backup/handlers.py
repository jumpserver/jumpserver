import os
import time
import pandas as pd
from collections import defaultdict

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from assets.models import AuthBook, Asset, BaseUser, ProtocolsMixin
from assets.notifications import AccountBackupExecutionTaskMsg
from applications.models import Account, Application
from applications.const import AppType
from users.models import User
from common.utils import get_logger
from common.utils.timezone import local_now_display
from common.utils.file import encrypt_and_compress_zip_file

logger = get_logger(__file__)

PATH = os.path.join(os.path.dirname(settings.BASE_DIR), 'tmp')


class AssetAccountHandler:
    @staticmethod
    def get_filename(plan_name):
        filename = os.path.join(
            PATH, f'{plan_name}-{_("Asset")}-{local_now_display()}-{time.time()}.xlsx'
        )
        return filename

    @staticmethod
    def create_df():
        df_dict = defaultdict(list)
        label_key = AuthBook._meta.verbose_name
        accounts = AuthBook.objects.all().prefetch_related('systemuser', 'asset')
        for account in accounts:
            account.load_auth()
            protocol = account.asset.protocol
            protocol_label = getattr(ProtocolsMixin.Protocol, protocol).label
            row = {
                getattr(Asset, 'hostname').field.verbose_name: account.asset.hostname,
                getattr(Asset, 'ip').field.verbose_name: account.asset.ip,
            }
            secret_row = AccountBackupHandler.create_secret_row(account)
            row.update(secret_row)
            row.update({
                getattr(Asset, 'protocol').field.verbose_name: protocol_label,
                getattr(AuthBook, 'version').field.verbose_name: account.version
            })
            df_dict[label_key].append(row)
        for k, v in df_dict.items():
            df_dict[k] = pd.DataFrame(v)
        return df_dict


class AppAccountHandler:
    @staticmethod
    def get_filename(plan_name):
        filename = os.path.join(
            PATH, f'{plan_name}-{_("Application")}-{local_now_display()}-{time.time()}.xlsx'
        )
        return filename

    @staticmethod
    def create_df():
        df_dict = defaultdict(list)
        accounts = Account.objects.all().prefetch_related('systemuser', 'app')
        for account in accounts:
            account.load_auth()
            app_type = account.app.type
            if app_type == 'postgresql':
                label_key = getattr(AppType, 'pgsql').label
            else:
                label_key = getattr(AppType, app_type).label
            row = {
                getattr(Application, 'name').field.verbose_name: account.app.name,
                getattr(Application, 'attrs').field.verbose_name: account.app.attrs
            }
            secret_row = AccountBackupHandler.create_secret_row(account)
            row.update(secret_row)
            row.update({
                getattr(Account, 'version').field.verbose_name: account.version
            })
            df_dict[label_key].append(row)
        for k, v in df_dict.items():
            df_dict[k] = pd.DataFrame(v)
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
            '\033[32m>>> 正在生成资产及应用相关备份信息文件\033[0m'
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

    @staticmethod
    def create_secret_row(instance):
        row = {
            getattr(BaseUser, 'username').field.verbose_name: instance.username,
            getattr(BaseUser, 'password').field.verbose_name: instance.password,
            getattr(BaseUser, 'private_key').field.verbose_name: instance.private_key,
            getattr(BaseUser, 'public_key').field.verbose_name: instance.public_key
        }
        return row
