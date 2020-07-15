from django.http import Http404
from django.core.exceptions import PermissionDenied
from rest_framework import exceptions
from rest_framework.views import set_rollback
from rest_framework.response import Response


class ExceptionHandlerType(type):
    def __new__(cls, name, bases, attrs: dict):
        handlers = set()
        for k, v in attrs.items():
            if k.startswith('handle') and callable(v):
                handlers.add(v.__name__)
        for base in bases:
            handlers.update(base.handler_names)
        attrs['handler_names'] = handlers
        return super().__new__(cls, name, bases, attrs)


class BaseExceptionHandler(metaclass=ExceptionHandlerType):
    handler_names = set()

    def __call__(self, exc, context):
        self.exc = exc
        self.context = context

        for handler_name in self.handler_names:
            handler = getattr(self, handler_name, lambda: None)
            tmp_exc = handler()
            if tmp_exc:
                exc = tmp_exc
                break

        if isinstance(exc, exceptions.APIException):
            headers = {}
            if getattr(exc, 'auth_header', None):
                headers['WWW-Authenticate'] = exc.auth_header
            if getattr(exc, 'wait', None):
                headers['Retry-After'] = '%d' % exc.wait

            if isinstance(exc.detail, (list, dict)):
                data = exc.detail
            else:
                data = {'detail': exc.detail}

            set_rollback()
            return Response(data, status=exc.status_code, headers=headers)

        return None

    def handle_http404(self):
        if isinstance(self.exc, Http404):
            return exceptions.NotFound()

    def handle_permission_denied(self):
        if isinstance(self.exc, PermissionDenied):
            return exceptions.PermissionDenied()
