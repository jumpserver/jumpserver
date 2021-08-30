# -*- coding: utf-8 -*-
from urllib3.exceptions import MaxRetryError
from urllib.parse import urlencode

from kubernetes.client import api_client
from kubernetes.client.api import core_v1_api
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from rest_framework.generics import get_object_or_404

from common.utils import get_logger
from common.tree import TreeNode
from assets.models import SystemUser

from .. import const

logger = get_logger(__file__)


class KubernetesClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token

    def get_api(self):
        configuration = client.Configuration()
        configuration.host = self.url
        configuration.verify_ssl = False
        configuration.api_key = {"authorization": "Bearer " + self.token}
        c = api_client.ApiClient(configuration=configuration)
        api = core_v1_api.CoreV1Api(c)
        return api

    def get_namespace_list(self):
        api = self.get_api()
        namespace_list = []
        for ns in api.list_namespace().items:
            namespace_list.append(ns.metadata.name)
        return namespace_list

    def get_services(self):
        api = self.get_api()
        ret = api.list_service_for_all_namespaces(watch=False)
        for i in ret.items:
            print("%s \t%s \t%s \t%s \t%s \n" % (
                i.kind, i.metadata.namespace, i.metadata.name, i.spec.cluster_ip, i.spec.ports))

    def get_pod_info(self, namespace, pod):
        api = self.get_api()
        resp = api.read_namespaced_pod(namespace=namespace, name=pod)
        return resp

    def get_pod_logs(self, namespace, pod):
        api = self.get_api()
        log_content = api.read_namespaced_pod_log(pod, namespace, pretty=True, tail_lines=200)
        return log_content

    def get_pods(self):
        api = self.get_api()
        try:
            ret = api.list_pod_for_all_namespaces(watch=False, _request_timeout=(3, 3))
        except MaxRetryError:
            logger.warning('Kubernetes connection timed out')
            return
        except ApiException as e:
            if e.status == 401:
                logger.warning('Kubernetes User not authenticated')
            else:
                logger.warning(e)
            return
        data = {}
        for i in ret.items:
            namespace = i.metadata.namespace
            pod_info = {
                'pod_name': i.metadata.name,
                'containers': [j.name for j in i.spec.containers]
            }
            if namespace in data:
                data[namespace].append(pod_info)
            else:
                data[namespace] = [pod_info, ]
        return data

    @staticmethod
    def get_kubernetes_data(app_id, system_user_id):
        from ..models import Application
        app = get_object_or_404(Application, id=app_id)
        system_user = get_object_or_404(SystemUser, id=system_user_id)
        k8s = KubernetesClient(app.attrs['cluster'], system_user.token)
        return k8s.get_pods()


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

    def as_namespace_pod_tree_node(self, name, meta, type, counts=0, is_container=False):
        from ..models import ApplicationTreeNodeMixin
        i = ApplicationTreeNodeMixin.create_tree_id(self.tree_id, type, name)
        meta.update({type: name})
        name = name if is_container else f'{name}({counts})'
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
        data = KubernetesClient.get_kubernetes_data(app_id, system_user_id)
        if not data:
            return tree_nodes

        if pod_name:
            for container in next(
                    filter(
                        lambda x: x['pod_name'] == pod_name, data[namespace]
                    )
            )['containers']:
                container_node = self.as_namespace_pod_tree_node(
                    container, parent_info, 'container', is_container=True
                )
                tree_nodes.append(container_node)
        elif namespace:
            for pod in data[namespace]:
                pod_nodes = self.as_namespace_pod_tree_node(
                    pod['pod_name'], parent_info, 'pod', len(pod['containers'])
                )
                tree_nodes.append(pod_nodes)
        elif system_user_id:
            for namespace, pods in data.items():
                namespace_node = self.as_namespace_pod_tree_node(
                    namespace, parent_info, 'namespace', len(pods)
                )
                tree_nodes.append(namespace_node)
        return tree_nodes
