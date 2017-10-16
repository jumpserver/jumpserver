# ~*~ coding: utf-8 ~*~


from rest_framework import viewsets, generics

from .tasks import ansible_install_role
from .hands import IsSuperUserOrAppUser
from .models import *
from .serializers import *
from django.core.exceptions import ValidationError


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

    def perform_create(self, serializer):
        #: 获取role name
        name = serializer.data['name']

        #: 执行role 安装操作
        ansible_install_role(name)

        #: 当Role不存在时才保存
        if not self.get_queryset().filter(name=name).exists():
            serializer.save()
