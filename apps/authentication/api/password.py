from django.core.cache import cache
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.serializers import PasswordVerifySerializer
from common.permissions import IsValidUser
from common.utils.random import random_string
from common.utils.timezone import timestamp
from authentication.mixins import authenticate
from authentication.errors import PasswordInvalid
from authentication.mixins import AuthMixin

from ..const import TEMP_PASSWORD


class UserPasswordVerifyApi(AuthMixin, CreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = PasswordVerifySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']
        user = self.request.user

        user = authenticate(request=request, username=user.username, password=password)
        if not user:
            raise PasswordInvalid

        self.mark_password_ok(user)
        return Response()


class TempPasswordApi(APIView):
    permission_classes = (IsValidUser,)
    expire_time = 300

    @staticmethod
    def get_temp_password(user_id):
        temp_password, created_time = None, None
        key = '%s_%s' % (TEMP_PASSWORD, user_id)
        temp_password_info = cache.get(key)
        if temp_password_info:
            temp_password = temp_password_info.get('temp_password')
            created_time = temp_password_info.get('created_time')
        return temp_password, created_time

    def get(self, request):
        results = []
        user = request.user
        temp_password, created_time = self.get_temp_password(user.id)
        if all([temp_password, created_time]):
            expire = timestamp() - created_time if created_time else None
            results = [{
                'temp_password': temp_password,
                'expire': self.expire_time - expire
            }]
        return Response({'count': len(results), 'results': results})

    def post(self, request):
        user = request.user
        temp_password, created_time = self.get_temp_password(user.id)
        cache.delete(temp_password)

        key = '%s_%s' % (TEMP_PASSWORD, user.id)
        temp_password = random_string(48)
        cache.set(key, {
            'temp_password': temp_password, 'created_time': timestamp()
        }, self.expire_time)
        cache.set(temp_password, user.id, self.expire_time)
        return Response({'msg': 'ok'})

    def delete(self, request):
        user = request.user
        key = '%s_%s' % (TEMP_PASSWORD, user.id)
        temp_password, create_time = self.get_temp_password(user.id)
        cache.delete(key)
        cache.delete(temp_password)
        return Response({'msg': 'ok'})
