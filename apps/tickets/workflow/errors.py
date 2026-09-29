from rest_framework.exceptions import APIException, ValidationError


class WorkflowConflict(APIException):
    status_code = 409
    default_detail = 'The workflow state has changed. Refresh before trying again.'
    default_code = 'workflow_conflict'


class WorkflowConfigurationError(ValidationError):
    default_code = 'invalid_workflow'
