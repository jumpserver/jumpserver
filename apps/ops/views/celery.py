# -*- coding: utf-8 -*-
#
from django.views.generic import DetailView, TemplateView

from common.permissions import AdminUserRequiredMixin
from ..models import CeleryTask


__all__ = ['CeleryTaskLogView']


class CeleryTaskLogView(AdminUserRequiredMixin, TemplateView):
    template_name = 'ops/celery_task_log.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'task_id': self.kwargs.get('pk')})
        return context
