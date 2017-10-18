# ~*~ coding: utf-8 ~*~


from rest_framework import status
from rest_framework import viewsets, generics
from rest_framework.response import Response

from .hands import IsSuperUserOrAppUser
from .serializers import *
from .tasks import ansible_install_role


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
        headers = self.get_success_headers(serializer.data)
        #: 安装失败返回错误
        return Response(serializer.data, status=status.HTTP_201_CREATED if self.result else status.HTTP_400_BAD_REQUEST,
                        headers=headers)
