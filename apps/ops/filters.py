from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from ops.const import AdHocModules, CreateMethods, JobStatus, Scope, Types
from ops.models import AdHoc, Job, JobExecution, Playbook


class JobFilterSet(BaseFilterSet):
    class Meta:
        model = Job
        fields = [
            'id', 'name', 'type', 'module', 'is_periodic', 'comment',
        ]


class AdHocFilterSet(BaseFilterSet):
    module = filters.ChoiceFilter(
        choices=AdHocModules.choices, label=_('Module')
    )
    scope = filters.ChoiceFilter(choices=Scope.choices, label=_('Scope'))
    creator = filters.UUIDFilter(
        field_name='creator_id', label=_('Creator ID')
    )

    class Meta:
        model = AdHoc
        fields = [
            'id', 'name', 'module', 'args', 'scope', 'creator', 'comment',
        ]


class PlaybookFilterSet(BaseFilterSet):
    scope = filters.ChoiceFilter(choices=Scope.choices, label=_('Scope'))
    creator = filters.UUIDFilter(
        field_name='creator_id', label=_('Creator ID')
    )
    create_method = filters.ChoiceFilter(
        choices=CreateMethods.choices, label=_('Create method')
    )

    class Meta:
        model = Playbook
        fields = [
            'id', 'name', 'scope', 'creator', 'create_method',
            'vcs_url', 'comment',
        ]


class JobExecutionFilterSet(BaseFilterSet):
    job_id = filters.UUIDFilter(field_name='job_id', label=_('Job ID'))
    task_id = filters.UUIDFilter(label=_('Task ID'))
    status = filters.ChoiceFilter(
        choices=JobStatus.choices, label=_('Status')
    )
    job_type = filters.ChoiceFilter(
        choices=Types.choices, label=_('Job type')
    )
    creator = filters.UUIDFilter(
        field_name='creator_id', label=_('Creator ID')
    )

    class Meta:
        model = JobExecution
        fields = [
            'id', 'task_id', 'job_id', 'material', 'job_type', 'status',
            'creator',
        ]
