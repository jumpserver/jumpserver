# -*- coding: utf-8 -*-
#
import paramiko
import socket
import time

from paramiko.ssh_exception import AuthenticationException, SSHException
from django.utils.translation import ugettext as _

from common.utils import get_logger


logger = get_logger(__file__)

__all__ = [
    'check_asset_can_run_ansible', 'clean_ansible_task_hosts',
    'group_asset_by_platform', 'group_asset_by_auth_type',
    'CustomSSHClient', 'color_string'
]


def check_asset_can_run_ansible(asset):
    if not asset.is_active:
        msg = _("Asset has been disabled, skipped: {}").format(asset)
        logger.info(msg)
        return False
    if not asset.is_support_ansible() or asset.exist_custom_command:
        msg = _("Asset may not be support ansible, skipped: {}").format(asset)
        logger.info(msg)
        return False
    return True


def check_system_user_can_run_ansible(system_user):
    if not system_user.auto_push:
        logger.warn(f'Push system user task skip, auto push not enable: system_user={system_user.name}')
        return False
    if not system_user.is_protocol_support_push:
        logger.warn(f'Push system user task skip, protocol not support: '
                    f'system_user={system_user.name} protocol={system_user.protocol} '
                    f'support_protocol={system_user.SUPPORT_PUSH_PROTOCOLS}')
        return False

    # Push root as system user is dangerous
    if system_user.username.lower() in ["root", "administrator"]:
        msg = _("For security, do not push user {}".format(system_user.username))
        logger.info(msg)
        return False

    return True


def clean_ansible_task_hosts(assets, system_user=None):
    if system_user and not check_system_user_can_run_ansible(system_user):
        return []
    cleaned_assets = []
    for asset in assets:
        if not check_asset_can_run_ansible(asset):
            continue
        cleaned_assets.append(asset)
    if not cleaned_assets:
        logger.info(_("No assets matched, stop task"))
    return cleaned_assets


def group_asset_by_platform(asset):
    if asset.is_unixlike():
        return 'unixlike'
    elif asset.is_windows():
        return 'windows'
    else:
        return 'other'


def group_asset_by_auth_type(assets):
    custom_asset = []
    ansible_asset = []
    for asset in assets:
        if asset.exist_custom_command:
            custom_asset.append(asset)
        else:
            ansible_asset.append(asset)
    return custom_asset, ansible_asset


def color_string(string, color='green'):
    color_map = {
        'red': '31m',
        'green': '32m'
    }
    color_ = color_map.get(color, '32m')
    return u'\033[{}{}\033[0m'.format(color_, string)


class CustomSSHClient:
    def __init__(self):
        self.client = None

    def init(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self, **connect_params):
        self.init()
        dark_msg = ''
        try:
            self.client.connect(**connect_params)
        except AuthenticationException as err:
            dark_msg = err
        except SSHException as err:
            dark_msg = err
        except Exception as err:
            dark_msg = err
        return dark_msg

    def exec_commands(self, commands, charset='utf8'):
        if self.client is None:
            return
        channel = self.client.invoke_shell()
        # 读取首次登陆终端返回的消息
        channel.recv(2048)
        # 终端登陆有延迟，等终端有返回后再执行命令
        time.sleep(0.5)
        result = ''
        for command in commands:
            try:
                channel.send(command + '\n')
            except socket.error as e:
                result += f'指令执行中断, 网络问题或者命令有误，详情查看后端日志输出'
                logger.warning('自定义改密平台执行改密失败，原因: %s', str(e))
                break
            time.sleep(0.3)
            result += channel.recv(1024).decode(encoding=charset)
        self.client.close()
        return result

    @staticmethod
    def is_login_success(err):
        return isinstance(err, AuthenticationException)

    def close(self):
        self.client.close()
