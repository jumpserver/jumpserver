# -*- coding: utf-8 -*-
#
from rest_framework.views import APIView
from rest_framework.views import Response
from django.core.mail import get_connection, send_mail
from django.utils.translation import ugettext_lazy as _

from .permissions import IsSuperUser
from .serializers import MailTestSerializer


class MailTestingAPI(APIView):
    permission_classes = (IsSuperUser,)
    serializer_class = MailTestSerializer
    success_message = _("Test mail sent to {}, please check")

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email_host_user = serializer.validated_data["EMAIL_HOST_USER"]
            kwargs = {
                "host": serializer.validated_data["EMAIL_HOST"],
                "port": serializer.validated_data["EMAIL_PORT"],
                "username": serializer.validated_data["EMAIL_HOST_USER"],
                "password": serializer.validated_data["EMAIL_HOST_PASSWORD"],
                "use_ssl": serializer.validated_data["EMAIL_USE_SSL"],
                "use_tls": serializer.validated_data["EMAIL_USE_TLS"]
            }
            connection = get_connection(timeout=5, **kwargs)

            try:
                connection.open()
            except Exception as e:
                return Response({"error": str(e)}, status=401)

            try:
                send_mail("Test", "Test smtp setting", email_host_user,
                          [email_host_user], connection=connection)
            except Exception as e:
                return Response({"error": str(e)}, status=401)

            return Response({"msg": self.success_message.format(email_host_user)})
