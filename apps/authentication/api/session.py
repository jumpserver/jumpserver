import uuid

from django.contrib.auth.models import AnonymousUser
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.sessions.cache import user_session_manager

__all__ = ['UserSessionApi']


class UserSessionApi(APIView):
    permission_classes = ()

    @staticmethod
    def get_client_id(request):
        client_id = request.data.get('client_id')
        try:
            return str(uuid.UUID(client_id))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValidationError({'client_id': 'A valid client ID is required.'}) from exc

    @staticmethod
    def get_response_data():
        return {
            'ok': True,
            'heartbeat_interval': user_session_manager.HEARTBEAT_INTERVAL,
            'lease_ttl': user_session_manager.LEASE_TTL,
        }

    def post(self, request, *args, **kwargs):
        if isinstance(request.user, AnonymousUser):
            return Response(status=status.HTTP_403_FORBIDDEN)

        client_id = self.get_client_id(request)
        connected = user_session_manager.renew(
            request.session.session_key, client_id
        )
        if connected is None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        data = self.get_response_data()
        data['ok'] = connected
        return Response(status=status.HTTP_200_OK, data=data)

    def delete(self, request, *args, **kwargs):
        if isinstance(request.user, AnonymousUser):
            return Response(status=status.HTTP_403_FORBIDDEN)

        client_id = self.get_client_id(request)
        user_session_manager.release(request.session.session_key, client_id)
        return Response(status=status.HTTP_200_OK, data={'ok': True})
