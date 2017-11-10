# ~*~ coding: utf-8 ~*~


from rest_framework import status
from rest_framework import viewsets, generics, mixins
from rest_framework.response import Response

from .hands import IsSuperUser, IsSuperUserOrAppUser, IsValidUser
from .serializers import *
from .tasks import ansible_install_role
import yaml
import os


class TaskListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
        对Ansible的task list的 展示 API操作
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (IsValidUser,)


class TaskOperationViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                           viewsets.GenericViewSet):
    """
        对Ansible的task提供的 操作 API操作
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (IsSuperUser,)

    def update(self, request, *args, **kwargs):
        response = super(TaskOperationViewSet, self).update(request, *args, **kwargs)
        self.playbook(self.get_object().id)
        return response

    def create(self, request, *args, **kwargs):
        response = super(TaskOperationViewSet, self).create(request, *args, **kwargs)
        self.playbook(response.data['id'])
        return response

    def playbook(self, task_id):
        """ 组织任务的playbook """
        task = Task.objects.get(id=task_id)
        playbook_json = [{'hosts': 'all', 'roles': [{'role': task.ansible_role.name}]}]
        if not os.path.exists('../playbooks'):
            os.makedirs('../playbooks')
        with open("../playbooks/task_%s.yml" % task.id, "w") as f:
            yaml.dump(playbook_json, f)


class AnsibleRoleViewSet(viewsets.ModelViewSet):
    """
        对AnsibleRole提供的API操作
    """
    queryset = AnsibleRole.objects.all()
    serializer_class = AnsibleRoleSerializer
    permission_classes = (IsSuperUser,)


class InstallRoleView(generics.CreateAPIView):
    """
        ansible-galaxy 安装 role
    """
    queryset = AnsibleRole.objects.all()
    serializer_class = AnsibleRoleSerializer
    permission_classes = (IsSuperUser,)
    result = None

    def perform_create(self, serializer):
        #: 获取role name

        #: 执行role 安装操作
        self.result = ansible_install_role(self.request.data['name'])
        #: 去掉参数中的版本
        name = str(self.request.data['name']).split(',')[0]
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


class TaskUpdateGroupApi(generics.RetrieveUpdateAPIView):
    """Task update it's group api"""
    queryset = Task.objects.all()
    serializer_class = TaskUpdateGroupSerializer
    permission_classes = (IsSuperUser,)


class TaskUpdateAssetApi(generics.RetrieveUpdateAPIView):
    """Task update it's asset api"""
    queryset = Task.objects.all()
    serializer_class = TaskUpdateAssetSerializer
    permission_classes = (IsSuperUser,)


class TaskUpdateSystemUserApi(generics.RetrieveUpdateAPIView):
    """Task update it's asset api"""
    queryset = Task.objects.all()
    serializer_class = TaskUpdateSystemUserSerializer
    permission_classes = (IsSuperUser,)


class TaskExecuteApi(generics.GenericAPIView):
    """
       Task Execute API
    """

    def get(self, request, *args, **kwargs):
        id = kwargs['pk']
        return Response(id)
