# ~*~ coding: utf-8 ~*~

from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_bulk import BulkModelViewSet

from .serializers import UserSerializer, UserGroupSerializer, \
    UserGroupUpdateMemeberSerializer, UserPKUpdateSerializer, \
    UserUpdateGroupSerializer
from .tasks import write_login_log_async
from .models import User, UserGroup
from .permissions import IsSuperUser, IsValidUser, IsCurrentUserOrReadOnly
from .utils import check_user_valid, generate_token
from common.mixins import IDInFilterMixin
from common.utils import get_logger


logger = get_logger(__name__)


class UserViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = User.objects.exclude(role="App")
    # queryset = User.objects.all().exclude(role="App").order_by("date_joined")
    serializer_class = UserSerializer
    permission_classes = (IsSuperUser,)
    filter_fields = ('username', 'email', 'name', 'id')


class UserUpdateGroupApi(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateGroupSerializer
    permission_classes = (IsSuperUser,)


class UserResetPasswordApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def perform_update(self, serializer):
        # Note: we are not updating the user object here.
        # We just do the reset-password stuff.
        import uuid
        from .utils import send_reset_password_mail
        user = self.get_object()
        user.password_raw = str(uuid.uuid4())
        user.save()
        send_reset_password_mail(user)


class UserResetPKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def perform_update(self, serializer):
        from .utils import send_reset_ssh_key_mail
        user = self.get_object()
        user.is_public_key_valid = False
        user.save()
        send_reset_ssh_key_mail(user)


class UserUpdatePKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserPKUpdateSerializer
    permission_classes = (IsCurrentUserOrReadOnly,)

    def perform_update(self, serializer):
        user = self.get_object()
        user.public_key = serializer.validated_data['_public_key']
        user.save()


class UserGroupViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer


class UserGroupUpdateUserApi(generics.RetrieveUpdateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupUpdateMemeberSerializer
    permission_classes = (IsSuperUser,)


class UserToken(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        if not request.user.is_authenticated:
            username = request.data.get('username', '')
            email = request.data.get('email', '')
            password = request.data.get('password', '')
            public_key = request.data.get('public_key', '')

            user, msg = check_user_valid(
                username=username, email=email,
                password=password, public_key=public_key)
        else:
            user = request.user
            msg = None
        if user:
            token = generate_token(request, user)
            return Response({'Token': token, 'Keyword': 'Bearer'}, status=200)
        else:
            return Response({'error': msg}, status=406)


class UserProfile(APIView):
    permission_classes = (IsValidUser,)

    def get(self, request):
        return Response(request.user.to_json())

    def post(self, request):
        return Response(request.user.to_json())


class UserAuthApi(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        public_key = request.data.get('public_key', '')
        login_type = request.data.get('login_type', '')
        login_ip = request.data.get('remote_addr', None)
        user_agent = request.data.get('HTTP_USER_AGENT', '')

        if not login_ip:
            login_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get("REMOTE_ADDR")

        user, msg = check_user_valid(
            username=username, password=password,
            public_key=public_key
        )

        if user:
            token = generate_token(request, user)
            write_login_log_async.delay(
                user.username, ip=login_ip,
                type=login_type, user_agent=user_agent,
            )
            return Response({'token': token, 'user': user.to_json()})
        else:
            return Response({'msg': msg}, status=401)
