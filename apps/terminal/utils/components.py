# -*- coding: utf-8 -*-
#
from itertools import groupby

from common.utils import get_logger


logger = get_logger(__name__)


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

