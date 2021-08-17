# -*- coding: utf-8 -*-
#
import os
from itertools import groupby

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.translation import ugettext as _

import jms_storage

from common.tasks import send_mail_async
from common.utils import get_logger, reverse
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


class ComputeStatUtil:
    # system status
    @staticmethod
    def _common_compute_system_status(value, thresholds):
        if thresholds[0] <= value <= thresholds[1]:
            return const.ComponentStatusChoices.normal.value
        elif thresholds[1] < value <= thresholds[2]:
            return const.ComponentStatusChoices.high.value
        else:
            return const.ComponentStatusChoices.critical.value

    @classmethod
    def _compute_system_stat_status(cls, stat):
        system_stat_thresholds_mapper = {
            'cpu_load': [0, 5, 20],
            'memory_used': [0, 85, 95],
            'disk_used': [0, 80, 99]
        }
        system_status = {}
        for stat_key, thresholds in system_stat_thresholds_mapper.items():
            stat_value = getattr(stat, stat_key)
            if stat_value is None:
                msg = 'stat: {}, stat_key: {}, stat_value: {}'
                logger.debug(msg.format(stat, stat_key, stat_value))
                stat_value = 0
            status = cls._common_compute_system_status(stat_value, thresholds)
            system_status[stat_key] = status
        return system_status

    @classmethod
    def compute_component_status(cls, stat):
        if not stat:
            return const.ComponentStatusChoices.offline
        system_status_values = cls._compute_system_stat_status(stat).values()
        if const.ComponentStatusChoices.critical in system_status_values:
            return const.ComponentStatusChoices.critical
        elif const.ComponentStatusChoices.high in system_status_values:
            return const.ComponentStatusChoices.high
        else:
            return const.ComponentStatusChoices.normal


class TypedComponentsStatusMetricsUtil(object):
    def __init__(self):
        self.components = []
        self.grouped_components = []
        self.get_components()

    def get_components(self):
        from .models import Terminal
        components = Terminal.objects.filter(is_deleted=False).order_by('type')
        grouped_components = groupby(components, lambda c: c.type)
        grouped_components = [(i[0], list(i[1])) for i in grouped_components]
        self.grouped_components = grouped_components
        self.components = components

    def get_metrics(self):
        metrics = []
        for _tp, components in self.grouped_components:
            normal_count = high_count = critical_count = 0
            total_count = offline_count = session_online_total = 0

            for component in components:
                total_count += 1
                if not component.is_alive:
                    offline_count += 1
                    continue
                if component.is_normal:
                    normal_count += 1
                elif component.is_high:
                    high_count += 1
                else:
                    # critical
                    critical_count += 1
                session_online_total += component.get_online_session_count()
            metrics.append({
                'total': total_count,
                'normal': normal_count,
                'high': high_count,
                'critical': critical_count,
                'offline': offline_count,
                'session_active': session_online_total,
                'type': _tp,
            })
        return metrics


class ComponentsPrometheusMetricsUtil(TypedComponentsStatusMetricsUtil):
    def __init__(self):
        super().__init__()
        self.metrics = self.get_metrics()

    @staticmethod
    def convert_status_metrics(metrics):
        return {
            'any': metrics['total'],
            'normal': metrics['normal'],
            'high': metrics['high'],
            'critical': metrics['critical'],
            'offline': metrics['offline']
        }

    def get_component_status_metrics(self):
        prometheus_metrics = list()
        # 各组件状态个数汇总
        prometheus_metrics.append('# JumpServer 各组件状态个数汇总')
        status_metric_text = 'jumpserver_components_status_total{component_type="%s", status="%s"} %s'
        for metric in self.metrics:
            tp = metric['type']
            prometheus_metrics.append(f'## 组件: {tp}')
            status_metrics = self.convert_status_metrics(metric)
            for status, value in status_metrics.items():
                metric_text = status_metric_text % (tp, status, value)
                prometheus_metrics.append(metric_text)
        return prometheus_metrics

    def get_component_session_metrics(self):
        prometheus_metrics = list()
        # 各组件在线会话数汇总
        prometheus_metrics.append('# JumpServer 各组件在线会话数汇总')
        session_active_metric_text = 'jumpserver_components_session_active_total{component_type="%s"} %s'

        for metric in self.metrics:
            tp = metric['type']
            prometheus_metrics.append(f'## 组件: {tp}')
            metric_text = session_active_metric_text % (tp, metric['session_active'])
            prometheus_metrics.append(metric_text)
        return prometheus_metrics

    def get_component_stat_metrics(self):
        prometheus_metrics = list()
        # 各组件节点指标
        prometheus_metrics.append('# JumpServer 各组件一些指标')
        state_metric_text = 'jumpserver_components_%s{component_type="%s", component="%s"} %s'
        stats_key = [
            'cpu_load', 'memory_used', 'disk_used', 'session_online'
        ]
        old_stats_key = [
            'system_cpu_load_1', 'system_memory_used_percent',
            'system_disk_used_percent', 'session_active_count'
        ]
        old_stats_key_mapper = dict(zip(stats_key, old_stats_key))

        for stat_key in stats_key:
            prometheus_metrics.append(f'## 指标: {stat_key}')
            for component in self.components:
                if not component.is_alive:
                    continue
                component_stat = component.latest_stat
                if not component_stat:
                    continue
                metric_text = state_metric_text % (
                    stat_key, component.type, component.name, getattr(component_stat, stat_key)
                )
                prometheus_metrics.append(metric_text)
                old_stat_key = old_stats_key_mapper.get(stat_key)
                old_metric_text = state_metric_text % (
                    old_stat_key, component.type, component.name, getattr(component_stat, stat_key)
                )
                prometheus_metrics.append(old_metric_text)
        return prometheus_metrics

    def get_prometheus_metrics_text(self):
        prometheus_metrics = list()
        for method in [
            self.get_component_status_metrics,
            self.get_component_session_metrics,
            self.get_component_stat_metrics
        ]:
            prometheus_metrics.extend(method())
            prometheus_metrics.append('\n')
        prometheus_metrics_text = '\n'.join(prometheus_metrics)
        return prometheus_metrics_text
