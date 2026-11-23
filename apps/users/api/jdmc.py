import hashlib
import hmac
import re
import time
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from rbac.models import Role, RoleBinding
from users.models import JDMCNodeBinding, User


class JDMCEnrollmentPermission(BasePermission):
    def has_permission(self, request, view):
        name = settings.JDMC_CORE_NODE_NAME
        secret_file = settings.JDMC_CORE_ENROLLMENT_SECRET_FILE
        if (not request.is_secure() or not settings.JDMC_ENABLED or not name or not secret_file
                or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,110}', name)
                or str(settings.SECURITY_SERVICE_ACCOUNT_REGISTRATION).lower() not in ('auto', 'true', '1')):
            return False
        scheme, _, token = request.headers.get('Authorization', '').partition(' ')
        if (scheme != 'BootstrapToken' or not token or not settings.BOOTSTRAP_TOKEN
                or not hmac.compare_digest(token.encode(), settings.BOOTSTRAP_TOKEN.encode())):
            return False
        if not isinstance(request.data, dict) or request.data.get('name') != name:
            return False
        stamp = request.headers.get('X-JDMC-Timestamp', '')
        nonce = request.headers.get('X-JDMC-Nonce', '')
        proof = request.headers.get('X-JDMC-Enrollment-Proof', '')
        if (not re.fullmatch(r'[0-9]{1,12}', stamp) or abs(time.time() - int(stamp)) > 120
                or not re.fullmatch(r'[0-9a-f]{64}', nonce) or not re.fullmatch(r'[0-9a-f]{64}', proof)):
            return False
        try:
            secret = Path(secret_file).read_bytes().strip()
        except OSError:
            return False
        if len(secret) < 32:
            return False
        message = f'jdmc-enrollment-v1\n{name}\n{stamp}\n{nonce}'.encode()
        if not hmac.compare_digest(hmac.new(secret, message, hashlib.sha256).hexdigest(), proof):
            return False
        return cache.add(f'jdmc-enrollment:{name}:{nonce}', '1', 241)


class JDMCNodeEnrollmentApi(APIView):
    authentication_classes = []
    permission_classes = [JDMCEnrollmentPermission]

    def post(self, request):
        name = settings.JDMC_CORE_NODE_NAME
        try:
            with transaction.atomic():
                # Serialize simultaneous first requests before the binding exists.
                role = Role.objects.select_for_update().get(id=Role.BuiltinRole.system_jdmc.id)
                binding = JDMCNodeBinding.objects.select_for_update().filter(pk=name).first()
                if binding is None:
                    if User.objects.filter(username=name).exists():
                        return Response({'detail': 'Node account name is already in use.'}, status=409)
                    user, key = User.create_service_account(name, name + User.service_account_email_suffix, 'JDMC node')
                    RoleBinding.objects.create(user=user, role=role)
                    JDMCNodeBinding.objects.create(name=name, user=user)
                    code = status.HTTP_201_CREATED
                else:
                    if not binding.user_id:
                        raise PermissionDenied('JDMC node has been revoked.')
                    user = User.objects.select_for_update().get(pk=binding.user_id)
                    roles = set(RoleBinding.objects_raw.filter(user=user).values_list('role_id', flat=True))
                    if not user.is_service_account or not user.is_valid or user.username != name or roles != {role.pk}:
                        raise PermissionDenied('JDMC node is disabled or its role has changed.')
                    key = user.access_keys.select_for_update().filter(is_active=True).order_by('-date_created', '-pk').first()
                    if key is None:
                        raise PermissionDenied('JDMC node has no active access key.')
                    code = status.HTTP_200_OK
                body = {'name': name, 'access_key': {'id': str(key.pk), 'secret': key.secret}}
        except IntegrityError:
            return Response({'detail': 'Node account identity conflicts with an existing account.'}, status=409)
        return Response(body, status=code, headers={'Cache-Control': 'no-store'})
