# -*- coding: utf-8 -*-
#
from django.views.generic import DetailView

from common.permissions import AdminUserRequiredMixin
from ..models import CeleryTask


__all__ = ['CeleryTaskLogView']


class CeleryTaskLogView(AdminUserRequiredMixin, DetailView):
    template_name = 'ops/celery_task_log.html'
    model = CeleryTask
