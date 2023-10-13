# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class JMSException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST


class JMSObjectDoesNotExist(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = 'object_does_not_exist'
    default_detail = _('%s object does not exist.')

    def __init__(self, detail=None, code=None, object_name=None):
        if detail is None and object_name:
            detail = self.default_detail % object_name
        super(JMSObjectDoesNotExist, self).__init__(detail=detail, code=code)


class SomeoneIsDoingThis(JMSException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _('Someone else is doing this. Please wait for complete')


class Timeout(JMSException):
    status_code = status.HTTP_408_REQUEST_TIMEOUT
    default_detail = _('Your request timeout')


class M2MReverseNotAllowed(JMSException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('M2M reverse not allowed')


class ReferencedByOthers(JMSException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'referenced_by_others'
    default_detail = _('Is referenced by other objects and cannot be deleted')


class UserConfirmRequired(JMSException):
    status_code = status.HTTP_412_PRECONDITION_FAILED

    def __init__(self, code=None):
        detail = {
            'type': 'user_confirm_required',
            'code': code,
            'detail': _('This action require confirm current user')
        }
        super().__init__(detail=detail, code=code)


class UnexpectError(JMSException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = 'unexpect_error'
    default_detail = _('Unexpect error occur')
