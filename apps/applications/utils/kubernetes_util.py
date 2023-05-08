# -*- coding: utf-8 -*-
from urllib.parse import urlencode

from kubernetes import client
from kubernetes.client import api_client
from kubernetes.client.api import core_v1_api
from rest_framework.generics import get_object_or_404

from assets.models import SystemUser
from common.tree import TreeNode
from common.utils import get_logger
from .. import const

logger = get_logger(__file__)


class KubernetesClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token

    @property
    def api(self):
        configuration = client.Configuration()
        configuration.host = self.url
        configuration.verify_ssl = False
        configuration.api_key = {"authorization": "Bearer " + self.token}
        c = api_client.ApiClient(configuration=configuration)
        api = core_v1_api.CoreV1Api(c)
        return api

    def get_namespaces(self):
        namespaces = []
        resp = self.api.list_namespace()
        for ns in resp.items:
            namespaces.append(ns.metadata.name)
        return namespaces

    def get_pods(self, namespace):
        pods = []
        resp = self.api.list_namespaced_pod(namespace)
        for pd in resp.items:
            pods.append(pd.metadata.name)
        return pods

    def get_containers(self, namespace, pod_name):
        containers = []
        resp = self.api.read_namespaced_pod(pod_name, namespace)
        for container in resp.spec.containers:
            containers.append(container.name)
        return containers

    @classmethod
    def run(cls, asset, secret, tp='namespace'):
        k8s_url = f'{asset.address}'
        k8s = cls(k8s_url, secret)
        func_name = f'get_{tp}s'
        if hasattr(k8s, func_name):
            return getattr(k8s, func_name)()
        return []

    @classmethod
    def get_kubernetes_data(cls, app_id, system_user_id, tp, *args):
        from ..models import Application
        app = get_object_or_404(Application, id=app_id)
        system_user = get_object_or_404(SystemUser, id=system_user_id)
        k8s = cls(app.attrs['cluster'], system_user.token)
        func_name = f'get_{tp}s'
        if hasattr(k8s, func_name):
            return getattr(k8s, func_name)(*args)
        return []


class KubernetesTree:
    def __init__(self, tree_id):
        self.tree_id = tree_id

    def as_tree_node(self, app):
        pid = app.create_app_tree_pid(self.tree_id)
        app_id = str(app.id)
        parent_info = {'app_id': app_id}
        node = self.create_tree_node(
            app_id, pid, app.name, 'k8s', parent_info
        )
        return node

    def as_system_user_tree_node(self, system_user, parent_info):
        from ..models import ApplicationTreeNodeMixin
        system_user_id = str(system_user.id)
        username = system_user.username
        username = username if username else '*'
        name = f'{system_user.name}({username})'
        pid = urlencode({'app_id': self.tree_id})
        i = ApplicationTreeNodeMixin.create_tree_id(pid, 'system_user_id', system_user_id)
        parent_info.update({'system_user_id': system_user_id})
        node = self.create_tree_node(
            i, pid, name, 'system_user', parent_info, icon='user-tie'
        )
        return node

    def as_namespace_pod_tree_node(self, name, meta, type, is_container=False):
        from ..models import ApplicationTreeNodeMixin
        i = ApplicationTreeNodeMixin.create_tree_id(self.tree_id, type, name)
        meta.update({type: name})
        node = self.create_tree_node(
            i, self.tree_id, name, type, meta, icon='cloud', is_container=is_container
        )
        return node

    @staticmethod
    def create_tree_node(id_, pid, name, identity, parent_info, icon='', is_container=False):
        node = TreeNode(**{
            'id': id_,
            'name': name,
            'title': name,
            'pId': pid,
            'isParent': not is_container,
            'open': False,
            'iconSkin': icon,
            'parentInfo': urlencode(parent_info),
            'meta': {
                'type': 'application',
                'data': {
                    'category': const.AppCategory.cloud,
                    'type': const.AppType.k8s,
                    'identity': identity
                }
            }
        })
        return node

    def async_tree_node(self, parent_info):
        pod_name = parent_info.get('pod')
        app_id = parent_info.get('app_id')
        namespace = parent_info.get('namespace')
        system_user_id = parent_info.get('system_user_id')

        tree_nodes = []
        if pod_name:
            tp = 'container'
            containers = KubernetesClient.get_kubernetes_data(
                app_id, system_user_id, tp, namespace, pod_name
            )
            for container in containers:
                container_node = self.as_namespace_pod_tree_node(
                    container, parent_info, tp, is_container=True
                )
                tree_nodes.append(container_node)
        elif namespace:
            tp = 'pod'
            pods = KubernetesClient.get_kubernetes_data(app_id, system_user_id, tp, namespace)
            for pod in pods:
                pod_node = self.as_namespace_pod_tree_node(
                    pod, parent_info, tp
                )
                tree_nodes.append(pod_node)
        elif system_user_id:
            tp = 'namespace'
            namespaces = KubernetesClient.get_kubernetes_data(app_id, system_user_id, tp)
            for namespace in namespaces:
                namespace_node = self.as_namespace_pod_tree_node(
                    namespace, parent_info, tp
                )
                tree_nodes.append(namespace_node)
        return tree_nodes
