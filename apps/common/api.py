# -*- coding: utf-8 -*-
#
import json

from rest_framework.views import APIView
from rest_framework.views import Response
from ldap3 import Server, Connection
from django.core.mail import get_connection, send_mail
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from .permissions import IsSuperUser, IsAppUser
from .serializers import MailTestSerializer, LDAPTestSerializer


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
        else:
            return Response({"error": str(serializer.errors)}, status=401)


class LDAPTestingAPI(APIView):
    permission_classes = (IsSuperUser,)
    serializer_class = LDAPTestSerializer
    success_message = _("Test ldap success")

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            host = serializer.validated_data["AUTH_LDAP_SERVER_URI"]
            bind_dn = serializer.validated_data["AUTH_LDAP_BIND_DN"]
            password = serializer.validated_data["AUTH_LDAP_BIND_PASSWORD"]
            use_ssl = serializer.validated_data.get("AUTH_LDAP_START_TLS", False)
            search_ou = serializer.validated_data["AUTH_LDAP_SEARCH_OU"]
            search_filter = serializer.validated_data["AUTH_LDAP_SEARCH_FILTER"]
            attr_map = serializer.validated_data["AUTH_LDAP_USER_ATTR_MAP"]

            try:
                attr_map = json.loads(attr_map)
            except json.JSONDecodeError:
                return Response({"error": "AUTH_LDAP_USER_ATTR_MAP not valid"}, status=401)

            server = Server(host, use_ssl=use_ssl)
            conn = Connection(server, bind_dn, password)
            try:
                conn.bind()
            except Exception as e:
                return Response({"error": str(e)}, status=401)

            ok = conn.search(search_ou, search_filter % ({"user": "*"}),
                             attributes=list(attr_map.values()))
            if not ok:
                return Response({"error": "Search no entry matched"}, status=401)

            users = []
            for entry in conn.entries:
                user = {}
                for attr, mapping in attr_map.items():
                    if hasattr(entry, mapping):
                        user[attr] = getattr(entry, mapping)
                users.append(user)
            if len(users) > 0:
                return Response({"msg": _("Match {} s users").format(len(users))})
            else:
                return Response({"error": "Have user but attr mapping error"}, status=401)
        else:
            return Response({"error": str(serializer.errors)}, status=401)


class DjangoSettingsAPI(APIView):
    def get(self, request):
        if not settings.DEBUG:
            return Response('Only debug mode support')

        configs = {}
        for i in dir(settings):
            if i.isupper():
                configs[i] = str(getattr(settings, i))
        return Response(configs)
