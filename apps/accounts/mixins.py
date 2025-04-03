from rest_framework.response import Response
from rest_framework import status
from django.db.models import Model
from django.utils import translation

from audits.const import ActionChoices
from audits.handler import create_or_update_operate_log


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

