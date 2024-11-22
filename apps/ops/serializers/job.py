import uuid

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import Asset, Node
from common.serializers import WritableNestedModelSerializer
from common.serializers.fields import ReadableHiddenField, ObjectRelatedField
from ops.mixin import PeriodTaskSerializerMixin
from ops.models import Job, JobExecution
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ops.serializers import JobVariableSerializer


class JobSerializer(BulkOrgResourceModelSerializer, PeriodTaskSerializerMixin, WritableNestedModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    run_after_save = serializers.BooleanField(label=_("Execute after saving"), default=False, required=False)
    date_last_run = serializers.DateTimeField(label=_('Date last run'), read_only=True)
    name = serializers.CharField(label=_('Name'), max_length=128, allow_blank=True, required=False)
    assets = serializers.PrimaryKeyRelatedField(label=_('Assets'), queryset=Asset.objects, many=True, required=False)
    nodes = ObjectRelatedField(label=_('Nodes'), queryset=Node.objects, many=True, required=False)
    variable = JobVariableSerializer(many=True, required=False, allow_null=True, label=_('Variable'))
    parameters = serializers.JSONField(label=_('Parameters'), default={}, write_only=True, required=False,
                                       allow_null=True)

    def to_internal_value(self, data):
        instant = data.get('instant', False)
        job_type = data.get('type', '')
        _uid = str(uuid.uuid4()).split('-')[-1]
        if instant:
            data['name'] = f'job-{_uid}'
        if job_type == 'upload_file':
            data['name'] = f'upload_file-{_uid}'
        return super().to_internal_value(data)

    def get_request_user(self):
        request = self.context.get('request')
        user = request.user if request else None
        return user

    def get_periodic_variable(self, variables):
        periodic_variable = {}
        for variable in variables:
            periodic_variable[variable['var_name']] = variable['default_value']
        return periodic_variable

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get('is_periodic') is True:
            attrs['periodic_variable'] = self.get_periodic_variable(attrs.get('variable', []))
        return attrs

    class Meta:
        model = Job
        read_only_fields = [
            "id", "date_last_run", "date_created",
            "date_updated", "average_time_cost", "created_by", "material"
        ]
        fields_m2m = ['variable']
        fields = read_only_fields + [
            "name", "instant", "type", "module",
            "args", "playbook", "assets",
            "runas_policy", "runas", "creator",
            "use_parameter_define", "parameters_define",
            "timeout", "chdir", "comment", "summary",
            "is_periodic", "interval", "crontab", "nodes",
            "run_after_save", "parameters", "periodic_variable"
        ] + fields_m2m
        extra_kwargs = {
            'average_time_cost': {'label': _('Duration')},
        }


class FileSerializer(serializers.Serializer):
    files = serializers.FileField(allow_empty_file=False, max_length=128)

    class Meta:
        ref_name = "JobFileSerializer"


class JobTaskStopSerializer(serializers.Serializer):
    task_id = serializers.CharField(max_length=128)

    class Meta:
        ref_name = "JobTaskStopSerializer"


class JobExecutionSerializer(BulkOrgResourceModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())
    job_type = serializers.ReadOnlyField(label=_("Job type"))
    material = serializers.ReadOnlyField(label=_("Command"))
    is_success = serializers.ReadOnlyField(label=_("Is success"))
    is_finished = serializers.ReadOnlyField(label=_("Is finished"))
    time_cost = serializers.ReadOnlyField(label=_("Time cost"))

    class Meta:
        model = JobExecution
        read_only_fields = ["id", "task_id", "timedelta", "time_cost",
                            'is_finished', 'date_start', 'date_finished',
                            'date_created', 'is_success', 'job_type',
                            'summary', 'material']
        fields = read_only_fields + [
            "job", "parameters", "creator"
        ]
        extra_kwargs = {
            "task_id": {
                "label": _("Task id"),
            },
            "job": {
                "label": _("Job"),
            }
        }

    def validate_job(self, job_obj):
        if job_obj.creator != self.context['request'].user:
            raise serializers.ValidationError(_("You do not have permission for the current job."))
        return job_obj

    @staticmethod
    def validate_parameters(parameters):
        prefix = "jms_"
        new_parameters = {}
        for key, value in parameters.items():
            if not key.startswith("jms_"):
                key = prefix + key
            new_parameters[key] = value
        return new_parameters
