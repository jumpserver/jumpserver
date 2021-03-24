from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from authentication.serializers import PasswordVerifySerializer
from common.permissions import IsValidUser
from authentication.mixins import authenticate
from authentication.errors import PasswdInvalid
from authentication.mixins import AuthMixin


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
            raise PasswdInvalid

        self.set_passwd_verify_on_session(user)
        return Response()
