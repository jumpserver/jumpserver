from requests import RequestException
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from common.jdmc import request_jdmc
from common.permissions import CanViewJDMC
from common.utils import get_logger


__all__ = ['JdmcSSOTokenAPI']


logger = get_logger(__file__)


class JdmcSSOTokenAPI(RetrieveAPIView):
    permission_classes = [CanViewJDMC]

    def retrieve(self, request, *args, **kwargs):
        username = request.user.username
        logger.info(f'User {username} is requesting JDMC SSO token')

        try:
            response = request_jdmc(
                method='POST',
                path='/jdmc/api/v1/auth/tokens',
                json={'name': username},
            )
        except RequestException as exc:
            return self.upstream_error(f'Failed to request JDMC SSO token: {exc}')

        if response.status_code != status.HTTP_200_OK:
            return self.upstream_error(
                'Failed to create JDMC SSO token, '
                f'status code: {response.status_code}, response: {response.text}'
            )

        try:
            payload = response.json()
        except ValueError:
            return self.upstream_error(
                f'Failed to decode JDMC SSO token response: {response.text}'
            )

        if payload.get('code') != 0:
            return self.upstream_error(
                f'Failed to create JDMC SSO token, response: {payload}'
            )

        token = payload.get('data', {}).get('token', '')
        if not isinstance(token, str) or not token.strip():
            return self.upstream_error(
                f'JDMC SSO token is missing from response: {payload}'
            )

        return Response({'token': token})

    @staticmethod
    def upstream_error(message):
        logger.error(message)
        return Response(
            {'error': message},
            status=status.HTTP_502_BAD_GATEWAY,
        )
