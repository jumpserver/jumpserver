# -*- coding: utf-8 -*-
#
from itertools import groupby

from common.utils import get_logger
from terminal.const import ComponentLoad, TerminalType

logger = get_logger(__name__)


class ComputeLoadUtil:
    # system status
    @staticmethod
    def _common_compute_system_status(value, thresholds):
        if thresholds[0] <= value <= thresholds[1]:
            return ComponentLoad.normal.value
        elif thresholds[1] < value <= thresholds[2]:
            return ComponentLoad.high.value
        else:
            return ComponentLoad.critical.value

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
    def compute_load(cls, stat, terminal_type=None):
        if not stat:
            # TODO The core component and celery component will return true for the time being.
            if terminal_type in [TerminalType.core, TerminalType.celery]:
                return ComponentLoad.normal
            else:
                return ComponentLoad.offline
        system_status_values = cls._compute_system_stat_status(stat).values()
        if ComponentLoad.critical in system_status_values:
            return ComponentLoad.critical
        elif ComponentLoad.high in system_status_values:
            return ComponentLoad.high
        else:
            return ComponentLoad.normal


class TypedComponentsStatusMetricsUtil(object):
    def __init__(self):
        self.components = []
        self.grouped_components = []
        self.get_components()

    def get_components(self):
        from ..models import Terminal
        components = Terminal.objects.filter(is_deleted=False).order_by('type')
        grouped_components = groupby(components, lambda c: c.type)
        grouped_components = [(i[0], list(i[1])) for i in grouped_components]
        self.grouped_components = grouped_components
        self.components = components

    def get_metrics(self):
        metrics = []
        for _tp, components in self.grouped_components:
            metric = {
                'total': 0,
                'type': _tp,
                'session_active': 0,
                ComponentLoad.high: [],
                ComponentLoad.normal: [],
                ComponentLoad.offline: [],
                ComponentLoad.critical: [],
            }
            for component in components:
                metric[component.load].append(component.name)
                metric['total'] += 1
                metric['session_active'] += component.get_online_session_count()
            metrics.append(metric)
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
                component_stat = component.last_stat
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
