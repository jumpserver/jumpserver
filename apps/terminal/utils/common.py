# -*- coding: utf-8 -*-
#

from common.utils import get_logger
from .. import const
from tickets.models import TicketSession


logger = get_logger(__name__)


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


def is_session_approver(session_id, user_id):
    ticket = TicketSession.get_ticket_by_session_id(session_id)
    if not ticket:
        return False
    ok = ticket.has_all_assignee(user_id)
    return ok
