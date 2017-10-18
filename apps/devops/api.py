# ~*~ coding: utf-8 ~*~


from rest_framework import viewsets, generics

from .tasks import ansible_install_role
from .hands import IsSuperUserOrAppUser
from .models import *
from .serializers import *
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response


class TaskViewSet(viewsets.ModelViewSet):
    """
        对Ansible的task提供的API操作
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (IsSuperUserOrAppUser,)


class AnsibleRoleViewSet(viewsets.ModelViewSet):
    """
        对AnsibleRole提供的API操作
    """
    queryset = AnsibleRole.objects.all()
    serializer_class = AnsibleRoleSerializer
    permission_classes = (IsSuperUserOrAppUser,)


class InstallRoleView(generics.CreateAPIView):
    """
        ansible-galaxy 安装 role
    """
    queryset = AnsibleRole.objects.all()
    serializer_class = AnsibleRoleSerializer
    permission_classes = (IsSuperUserOrAppUser,)
    result = None

    def perform_create(self, serializer):
        #: 获取role name

        #: 执行role 安装操作
        self.result = ansible_install_role(serializer.data['name'])
        #: 去掉参数中的版本
        name = str(serializer.data['name']).split(',')[0]
        #: 当执行成功且Role不存在时才保存
        if self.result and not self.get_queryset().filter(name=name).exists():
            serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        #: 安装成功返回数据库中存在的Role  不成功的数据没有id
        if self.result:
            name = str(serializer.data['name']).split(',')[0]
            serializer = AnsibleRoleSerializer(self.get_queryset().get(name=name))
            headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
