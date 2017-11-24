# ~*~ coding: utf-8 ~*~

import uuid
from rest_framework import status
from rest_framework import viewsets, generics, mixins, views
from rest_framework.response import Response

from .hands import IsSuperUser, IsSuperUserOrAppUser, IsValidUser
from rest_framework import permissions
from .serializers import *
from .tasks import ansible_install_role, ansible_task_execute
import yaml
import os
from perms import utils
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import make_password, check_password


class TaskListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
        对Ansible的task list的 展示 API操作
    """
    queryset = Task.objects.all()
    serializer_class = TaskReadSerializer
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
        task = self.get_object()
        self.playbook(task.id)
        return response

    def create(self, request, *args, **kwargs):
        response = super(TaskOperationViewSet, self).create(request, *args, **kwargs)
        self.playbook(response.data['id'])
        return response

    def playbook(self, task_id):
        """ 组织任务的playbook """
        task = Task.objects.get(id=task_id)
        playbook = {'hosts': 'all'}
        #: system_user
        if task.system_user is not None:
            playbook.update({'become': 'True', 'become_user': task.system_user.username})

        #: role
        role = {'roles': [{'role': task.ansible_role.name}]}
        playbook.update(role)

        playbook_yml = [playbook]
        if not os.path.exists('../playbooks'):
            os.makedirs('../playbooks')
        with open("../playbooks/task_%s.yml" % task.id, "w") as f:
            yaml.dump(playbook_yml, f)


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
        #: 新建role安装文件夹
        roles_path = os.path.join(settings.PROJECT_DIR, 'playbooks', 'roles')
        #: 获取role name

        #: 执行role 安装操作
        self.result = ansible_install_role(self.request.data['name'], roles_path)
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


class InstallZipRoleView(generics.CreateAPIView):
    """
        ansible-galaxy 安装 role
    """
    queryset = AnsibleRole.objects.all()
    serializer_class = AnsibleRoleSerializer
    permission_classes = (IsSuperUser,)

    def create(self, request, *args, **kwargs):
        file = request.FILES['file_data']
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        #: 保存
        path = default_storage.save(os.path.join(settings.MEDIA_ROOT, 'tmp', '{}.zip'.format(file.name)),
                                    ContentFile(file.read()))
        #: 解压
        import zipfile
        f = zipfile.ZipFile(path, 'r')
        for file in f.namelist():
            f.extract(file, os.path.join(settings.PROJECT_DIR, 'playbooks', 'roles'))

        #: 删除
        default_storage.delete(path)

        #: 保存实例
        if not self.get_queryset().filter(name=request.data['name']).exists():
            serializer.save()
        headers = self.get_success_headers(serializer.data)
        #: 返回
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


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
    """Task update it's system_user api"""
    queryset = Task.objects.all()
    serializer_class = TaskUpdateSystemUserSerializer
    permission_classes = (IsSuperUser,)


class TaskExecuteApi(generics.RetrieveAPIView):
    """
       Task Execute API
    """
    permission_classes = (IsValidUser,)
    queryset = Task.objects.all()

    def get(self, request, *args, **kwargs):
        task = self.get_object()
        #: 计算assets
        #: 超级用户直接取task所有assets
        assets = []
        assets.extend(list(task.assets.all()))
        for group in task.groups.all():
            assets.extend(group.assets.all())

        if not request.user.is_superuser:
            #: 普通用户取授权过的assets
            granted_assets = utils.get_user_granted_assets(user=request.user)
            #: 取交集
            assets = set(assets).intersection(set(granted_assets))

        if len(assets) == 0:
            return Response("任务执行的资产为空", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        #: 系统用户不能为空
        if task.system_user is None:
            return Response("任务执行的系统用户为空", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            #: 没有assets和system_user不允许执行

        #: 新建一个Record
        uuid_str = str(uuid.uuid4())

        playbook_path = '../playbooks/task_%d.yml' % task.id
        task_name = "%s #%d" % (task.name, task.counts + 1)
        with open(playbook_path) as f:
            playbook_json = yaml.load(f)
        task_record = Record(uuid=uuid_str,
                             name=task_name,
                             assets=','.join(str(asset._to_secret_json()['id']) for asset in assets),
                             module_args=[('playbook', playbook_json)])
        task_record.task = task
        task_record.save()

        ansible_task_execute.delay(task.id, [asset._to_secret_json() for asset in assets],
                                   task.system_user.username, task_name, task.tags, uuid_str)
        task.counts += 1
        task.save()

        return Response(uuid_str, status=status.HTTP_200_OK)


class RecordViewSet(viewsets.ModelViewSet):
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    permission_classes = (IsValidUser,)

    def get_queryset(self):
        task = self.request.query_params.get('task', '')
        queryset = self.queryset
        if task:
            queryset = queryset.filter(task_id=task).order_by('-date_start')[:10]
        return queryset


class VariableViewSet(viewsets.ModelViewSet):
    queryset = Variable.objects.all()
    serializer_class = VariableSerializer
    permission_classes = (IsSuperUser,)


class VariableVarsApi(generics.RetrieveAPIView):
    """
       Vars Read API
    """
    permission_classes = (IsSuperUser,)
    queryset = Variable.objects.all()

    def retrieve(self, request, *args, **kwargs):
        variable = self.get_object()
        result = []
        for key, value in variable.vars.items():
            result.append({"key": key, "value": value})
        return Response(result, status=status.HTTP_200_OK)


class VariableAddVarsApi(generics.UpdateAPIView):
    """
       Vars Add API
    """
    permission_classes = (IsSuperUser,)
    queryset = Variable.objects.all()
    serializer_class = VariableVarSerializer

    def put(self, request, *args, **kwargs):
        variable = self.get_object()
        variable.vars.update({request.data['key']: request.data['value']})
        variable.save()
        return Response(variable.vars, status=status.HTTP_200_OK)


class VariableDeleteVarsApi(generics.DestroyAPIView):
    """
       Vars Add API
    """
    permission_classes = (IsSuperUser,)
    queryset = Variable.objects.all()
    serializer_class = VariableVarSerializer

    def delete(self, request, *args, **kwargs):
        variable = self.get_object()
        variable.vars.pop(request.data['key'])
        variable.save()
        return Response(variable.vars, status=status.HTTP_200_OK)


class VariableUpdateGroupApi(generics.UpdateAPIView):
    """Variable update it's group api"""
    queryset = Variable.objects.all()
    serializer_class = VariableUpdateGroupSerializer
    permission_classes = (IsSuperUser,)


class VariableUpdateAssetApi(generics.UpdateAPIView):
    """Variable update it's asset api"""
    queryset = Variable.objects.all()
    serializer_class = VariableUpdateAssetSerializer
    permission_classes = (IsSuperUser,)


class VariableGetAssetApi(generics.RetrieveAPIView):
    """Variable update it's asset api"""
    queryset = Variable.objects.all()
    serializer_class = AssetSerializer
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        serializer = AssetSerializer(self.get_object().assets.all(), many=True)
        return Response(serializer.data)


class VariableGetGroupApi(generics.RetrieveAPIView):
    """Variable update it's asset api"""
    queryset = Variable.objects.all()
    serializer_class = AssetGroupSerializer
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        serializer = AssetGroupSerializer(self.get_object().groups.all(), many=True)
        return Response(serializer.data)


class TaskWebhookApi(generics.GenericAPIView):
    """
       Task Execute API
    """
    permission_classes = (permissions.AllowAny,)
    queryset = Task.objects.all()
    serializer_class = TaskWebhookSerializer

    def post(self, request, *args, **kwargs):
        task = self.get_object()
        #: 计算assets
        #: 超级用户直接取task所有assets
        assets = list(task.assets.all())

        password_raw = request.data['password']

        result = task.check_password(password_raw)  # check_password 返回值为一个Bool类型，验证密码的正确与否
        #: 新建一个Record
        uuid_str = str(uuid.uuid4())

        playbook_path = '../playbooks/task_%d.yml' % task.id
        task_name = "%s %s #%d" % (task.name, 'WebHook', task.counts + 1)
        with open(playbook_path) as f:
            playbook_json = yaml.load(f)
        task_record = Record(uuid=uuid_str,
                             name=task_name,
                             assets=','.join(str(asset._to_secret_json()['id']) for asset in assets),
                             module_args=[('playbook', playbook_json)])
        task_record.task = task

        if not result:
            task_record.is_success = False
            task_record.is_finished = False
            task_record.result = {"msg": "任务密码不匹配", "data": kwargs}
            return Response("任务密码不匹配", status=status.HTTP_400_BAD_REQUEST)
        if len(assets) == 0:
            task_record.is_success = False
            task_record.is_finished = False
            task_record.result = {"msg": "任务执行的资产为空", "data": kwargs}
            return Response("任务执行的资产为空", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        #: 系统用户不能为空
        if task.system_user is None:
            task_record.is_success = False
            task_record.is_finished = False
            task_record.result = {"msg": "任务执行的系统用户为空", "data": kwargs}
            return Response("任务执行的系统用户为空", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            #: 没有assets和system_user不允许执行

        task_record.save()

        ansible_task_execute.delay(task.id, [asset._to_secret_json() for asset in assets],
                                   task.system_user.username, task_name, task.tags, uuid_str)
        task.counts += 1
        task.save()

        return Response(uuid_str, status=status.HTTP_200_OK)
