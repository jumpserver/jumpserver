from rest_framework.response import Response
from rest_framework import status
from django.db.models import Model
from django.utils import translation

from audits.const import ActionChoices
from audits.handler import create_or_update_operate_log
from accounts.const import AuditEvent
from accounts.credential_client.audit import ApplicationAuditContext
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import CredentialClientInstance
from common.utils import get_request_ip


class AccountRecordViewLogMixin(object):
    get_object: callable
    model: Model

    def retrieve(self, request, *args, **kwargs):
        retrieve_func = getattr(super(), 'retrieve')
        if not callable(retrieve_func):
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        response = retrieve_func(request, *args, **kwargs)
        with translation.override('en'):
            create_or_update_operate_log(
                ActionChoices.view, self.model._meta.verbose_name,
                force=True, resource=self.get_object(),
            )
        return response


class ApplicationAuditMixin:
    client_audit_events = {}

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        event = self.client_audit_events.get(self.action)
        if event:
            self.start_client_audit(event, track_fetch=event == AuditEvent.CREDENTIAL_FETCHED)

    def start_audit(self, event, **values):
        context = ApplicationAuditContext(event=event, values=values)
        self.request._request.application_audit = context
        return context

    def get_client_manager(self, data):
        context = getattr(self.request._request, 'application_audit', None)
        if context is not None:
            context.set_request_data(data)
        return CredentialClientManager(
            self.request.user, data.get('configuration_id'), data.get('instance_id', ''),
            audit_context=context,
        )

    def start_client_audit(self, event, track_fetch=False):
        user = self.request.user
        params = self.request.query_params
        if isinstance(user, CredentialClientInstance):
            context = self.start_audit(event, client=user)
            application = user.application
            client_type = user.type
            configuration_id = str(user.configuration_id)
            instance_id = user.instance_id
        else:
            context = self.start_audit(event, application=user)
            application = user
            client_type = 'sdk'
            configuration_id = params.get('configuration_id', '')
            instance_id = params.get('instance_id', '')

        if track_fetch:
            # An SDK instance created by a failed first fetch is rolled back; its PK is not stable.
            context.fetch_identity = [
                str(application.org_id), str(application.id), client_type,
                configuration_id, instance_id, params.get('key', ''), get_request_ip(self.request),
            ]
        return context

    def handle_exception(self, exc):
        context = getattr(self.request._request, 'application_audit', None)
        if context is not None and hasattr(exc, 'get_codes'):
            codes = exc.get_codes()
            while isinstance(codes, (dict, list)) and codes:
                if isinstance(codes, dict):
                    codes = next(iter(codes.values()))
                else:
                    codes = codes[0]
            if isinstance(codes, str):
                context.error_code = codes[:128]
        return super().handle_exception(exc)

    def get_object(self):
        instance = super().get_object()
        if self.request.method != 'GET':
            from accounts.credential_client.audit_signals import get_audit_context
            self.start_audit(AuditEvent.CONFIGURATION_UPDATED, **get_audit_context(instance))
        return instance
