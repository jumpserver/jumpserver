# -*- coding: utf-8 -*-
#
import os

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.translation import ugettext as _

import jms_storage

from common.tasks import send_mail_async
from common.utils import get_logger, reverse
from settings.models import Setting
from . import const

from .models import ReplayStorage, Session, Command

logger = get_logger(__name__)


def find_session_replay_local(session):
    # 新版本和老版本的文件后缀不同
    session_path = session.get_rel_replay_path()  # 存在外部存储上的路径
    local_path = session.get_local_path()
    local_path_v1 = session.get_local_path(version=1)

    # 去default storage中查找
    for _local_path in (local_path, local_path_v1, session_path):
        if default_storage.exists(_local_path):
            url = default_storage.url(_local_path)
            return _local_path, url
    return None, None


def download_session_replay(session):
    session_path = session.get_rel_replay_path()  # 存在外部存储上的路径
    local_path = session.get_local_path()
    replay_storages = ReplayStorage.objects.all()
    configs = {
        storage.name: storage.config
        for storage in replay_storages
        if not storage.type_null_or_server
    }
    if settings.SERVER_REPLAY_STORAGE:
        configs['SERVER_REPLAY_STORAGE'] = settings.SERVER_REPLAY_STORAGE
    if not configs:
        msg = "Not found replay file, and not remote storage set"
        return None, msg

    # 保存到storage的路径
    target_path = os.path.join(default_storage.base_location, local_path)
    target_dir = os.path.dirname(target_path)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    storage = jms_storage.get_multi_object_storage(configs)
    ok, err = storage.download(session_path, target_path)
    if not ok:
        msg = "Failed download replay file: {}".format(err)
        logger.error(msg)
        return None, msg
    url = default_storage.url(local_path)
    return local_path, url


def get_session_replay_url(session):
    local_path, url = find_session_replay_local(session)
    if local_path is None:
        local_path, url = download_session_replay(session)
    return local_path, url


def send_command_alert_mail(command):
    session_obj = Session.objects.get(id=command['session'])

    input = command['input']
    if isinstance(input, str):
        input = input.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

    subject = _("Insecure Command Alert: [%(name)s->%(login_from)s@%(remote_addr)s] $%(command)s") % {
                    'name': command['user'],
                    'login_from': session_obj.get_login_from_display(),
                    'remote_addr': session_obj.remote_addr,
                    'command': input
                 }

    recipient_list = settings.SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER.split(',')
    message = _("""
        Command: %(command)s
        <br>
        Asset: %(host_name)s (%(host_ip)s)
        <br>
        User: %(user)s
        <br>
        Level: %(risk_level)s
        <br>
        Session: <a href="%(session_detail_url)s">session detail</a>
        <br>
        """) % {
            'command': command['input'],
            'host_name': command['asset'],
            'host_ip': session_obj.asset_obj.ip,
            'user': command['user'],
            'risk_level': Command.get_risk_level_str(command['risk_level']),
            'session_detail_url': reverse('api-terminal:session-detail',
                                          kwargs={'pk': command['session']},
                                          external=True, api_to_ui=True),
        }
    logger.debug(message)

    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def send_command_execution_alert_mail(command):
    subject = _("Insecure Web Command Execution Alert: [%(name)s]") % {
                    'name': command['user'],
                 }
    input = command['input']
    input = input.replace('\n', '<br>')
    recipient_list = settings.SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER.split(',')

    assets = ', '.join([str(asset) for asset in command['assets']])
    message = _("""
        <br>
        Assets: %(assets)s
        <br>
        User: %(user)s
        <br>
        Level: %(risk_level)s
        <br>

        ----------------- Commands ---------------- <br>
        %(command)s <br>
        ----------------- Commands ---------------- <br>
        """) % {
            'command': input,
            'assets': assets,
            'user': command['user'],
            'risk_level': Command.get_risk_level_str(command['risk_level']),
        }

    send_mail_async.delay(subject, message, recipient_list, html_message=message)


class ComponentsMetricsUtil(object):

    @staticmethod
    def get_components(tp=None):
        from .models import Terminal
        components = Terminal.objects.filter(is_deleted=False).order_by('type')
        if tp:
            components = components.filter(type=tp)
        return components

    def get_metrics(self, tp=None):
        components = self.get_components(tp)
        total_count = normal_count = high_count = critical_count = offline_count = \
            session_active_total = 0
        for component in components:
            total_count += 1
            if component.is_alive:
                if component.is_normal:
                    normal_count += 1
                elif component.is_high:
                    high_count += 1
                else:
                    # critical
                    critical_count += 1
                session_active_total += component.state.get('session_active_count', 0)
            else:
                offline_count += 1
        return {
            'total': total_count,
            'normal': normal_count,
            'high': high_count,
            'critical': critical_count,
            'offline': offline_count,
            'session_active': session_active_total
        }


class ComponentsPrometheusMetricsUtil(ComponentsMetricsUtil):

    @staticmethod
    def convert_status_metrics(metrics):
        return {
            'any': metrics['total'],
            'normal': metrics['normal'],
            'high': metrics['high'],
            'critical': metrics['critical'],
            'offline': metrics['offline']
        }

    def get_prometheus_metrics_text(self):
        prometheus_metrics = list()

        # 各组件状态个数汇总
        prometheus_metrics.append('# JumpServer 各组件状态个数汇总')
        status_metric_text = 'jumpserver_components_status_total{component_type="%s", status="%s"} %s'
        for tp in const.TerminalTypeChoices.types():
            prometheus_metrics.append(f'## 组件: {tp}')
            metrics_tp = self.get_metrics(tp)
            status_metrics = self.convert_status_metrics(metrics_tp)
            for status, value in status_metrics.items():
                metric_text = status_metric_text % (tp, status, value)
                prometheus_metrics.append(metric_text)

        prometheus_metrics.append('\n')

        # 各组件在线会话数汇总
        prometheus_metrics.append('# JumpServer 各组件在线会话数汇总')
        session_active_metric_text = 'jumpserver_components_session_active_total{component_type="%s"} %s'
        for tp in const.TerminalTypeChoices.types():
            prometheus_metrics.append(f'## 组件: {tp}')
            metrics_tp = self.get_metrics(tp)
            metric_text = session_active_metric_text % (tp, metrics_tp['session_active'])
            prometheus_metrics.append(metric_text)

        prometheus_metrics.append('\n')

        # 各组件节点指标
        prometheus_metrics.append('# JumpServer 各组件一些指标')
        state_metric_text = 'jumpserver_components_%s{component_type="%s", component="%s"} %s'
        states = [
            'system_cpu_load_1', 'system_memory_used_percent',
            'system_disk_used_percent', 'session_active_count'
        ]
        for state in states:
            prometheus_metrics.append(f'## 指标: {state}')
            components = self.get_components()
            for component in components:
                if not component.is_alive:
                    continue
                metric_text = state_metric_text % (
                    state, component.type, component.name, component.state.get(state)
                )
                prometheus_metrics.append(metric_text)

        prometheus_metrics_text = '\n'.join(prometheus_metrics)
        return prometheus_metrics_text
