import os
import time
from openpyxl import Workbook
from collections import defaultdict, OrderedDict

from django.conf import settings
from django.db.models import F
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.models import AuthBook, SystemUser, Asset
from assets.serializers import AccountBackUpSerializer
from assets.notifications import AccountBackupExecutionTaskMsg
from applications.models import Account, Application
from applications.const import AppType
from applications.serializers import AppAccountBackUpSerializer
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
    def get_header_fields(cls, serializer: serializers.Serializer):
        try:
            backup_fields = getattr(serializer, 'Meta').fields
        except AttributeError:
            backup_fields = serializer.fields.keys()
        header_fields = {}
        for field in backup_fields:
            v = serializer.fields[field]
            if isinstance(v, serializers.Serializer):
                _fields = cls.get_header_fields(v)
                header_fields.update(_fields)
            else:
                header_fields[field] = str(v.label)
        return header_fields

    @staticmethod
    def load_auth(tp, value, system_user):
        if value:
            return value
        if system_user:
            return getattr(system_user, tp, '')
        return ''

    @classmethod
    def replace_auth(cls, account, system_user_dict):
        system_user = system_user_dict.get(account.systemuser_id)
        account.username = cls.load_auth('username', account.username, system_user)
        account.password = cls.load_auth('password', account.password, system_user)
        account.private_key = cls.load_auth('private_key', account.private_key, system_user)
        account.public_key = cls.load_auth('public_key', account.public_key, system_user)
        return account

    @classmethod
    def create_row(cls, data, header_fields):
        data = cls.unpack_data(data)
        row_dict = {}
        for field, header_name in header_fields.items():
            row_dict[header_name] = str(data.get(field, field))
        return row_dict

    @classmethod
    def add_rows(cls, data, header_fields, sheet):
        data_map = defaultdict(list)
        for i in data:
            row = cls.create_row(i, header_fields)
            if sheet not in data_map:
                data_map[sheet].append(list(row.keys()))
            data_map[sheet].append(list(row.values()))
        return data_map


class AssetAccountHandler(BaseAccountHandler):
    @staticmethod
    def get_filename(plan_name):
        filename = os.path.join(
            PATH, f'{plan_name}-{_("Asset")}-{local_now_display()}-{time.time()}.xlsx'
        )
        return filename

    @classmethod
    def replace_account_info(cls, account, asset_dict, system_user_dict):
        asset = asset_dict.get(account.asset_id)
        account.ip = asset.ip if asset else ''
        account.hostname = asset.hostname if asset else ''
        account = cls.replace_auth(account, system_user_dict)
        return account

    @classmethod
    def create_data_map(cls, system_user_dict):
        sheet_name = AuthBook._meta.verbose_name
        assets = Asset.objects.only('id', 'hostname', 'ip')
        asset_dict = {asset.id: asset for asset in assets}
        accounts = AuthBook.objects.all()
        if not accounts.exists():
            return

        header_fields = cls.get_header_fields(AccountBackUpSerializer(accounts.first()))
        for account in accounts:
            cls.replace_account_info(account, asset_dict, system_user_dict)
        data = AccountBackUpSerializer(accounts, many=True).data
        data_map = cls.add_rows(data, header_fields, sheet_name)
        logger.info('\n\033[33m- 共收集 {} 条资产账号\033[0m'.format(accounts.count()))
        return data_map


class AppAccountHandler(BaseAccountHandler):
    @staticmethod
    def get_filename(plan_name):
        filename = os.path.join(
            PATH, f'{plan_name}-{_("Application")}-{local_now_display()}-{time.time()}.xlsx'
        )
        return filename

    @classmethod
    def replace_account_info(cls, account, app_dict, system_user_dict):
        app = app_dict.get(account.app_id)
        account.type = app.type if app else ''
        account.app_display = app.name if app else ''
        account.category = app.category if app else ''
        account = cls.replace_auth(account, system_user_dict)
        return account

    @classmethod
    def create_data_map(cls, system_user_dict):
        apps = Application.objects.only('id', 'type', 'name', 'category')
        app_dict = {app.id: app for app in apps}
        qs = Account.objects.all().annotate(app_type=F('app__type'))
        if not qs.exists():
            return

        account_type_map = defaultdict(list)
        for i in qs:
            account_type_map[i.app_type].append(i)
        data_map = {}
        for app_type, accounts in account_type_map.items():
            sheet_name = AppType.get_label(app_type)
            header_fields = cls.get_header_fields(AppAccountBackUpSerializer(tp=app_type))
            if not accounts:
                continue
            for account in accounts:
                cls.replace_account_info(account, app_dict, system_user_dict)
            data = AppAccountBackUpSerializer(accounts, many=True, tp=app_type).data
            data_map.update(cls.add_rows(data, header_fields, sheet_name))
        logger.info('\n\033[33m- 共收集{}条应用账号\033[0m'.format(qs.count()))
        return data_map


handler_map = {
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
        files = []
        system_user_qs = SystemUser.objects.only(
            'id', 'username', 'password', 'private_key', 'public_key'
        )
        system_user_dict = {i.id: i for i in system_user_qs}
        for account_type in self.execution.types:
            handler = handler_map.get(account_type)
            if not handler:
                continue

            data_map = handler.create_data_map(system_user_dict)
            if not data_map:
                continue

            filename = handler.get_filename(self.plan_name)

            wb = Workbook(filename)
            for sheet, data in data_map.items():
                ws = wb.create_sheet(str(sheet))
                for row in data:
                    ws.append(row)
            wb.save(filename)
            files.append(filename)
        timedelta = round((time.time() - time_start), 2)
        logger.info('步骤完成: 用时 {}s'.format(timedelta))
        return files

    def send_backup_mail(self, files, recipients):
        if not files:
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
            recipients = self.execution.plan_snapshot.get('recipients')
            if not recipients:
                logger.info(
                    '\n'
                    '\033[32m>>> 该备份任务未分配收件人\033[0m'
                    ''
                )
            else:
                files = self.create_excel()
                self.send_backup_mail(files, recipients)
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
