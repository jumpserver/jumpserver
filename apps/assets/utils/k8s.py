# -*- coding: utf-8 -*-
from urllib3.exceptions import MaxRetryError
from urllib.parse import urlencode, parse_qsl

from kubernetes import client
from kubernetes.client import api_client
from kubernetes.client.api import core_v1_api
from kubernetes.client.exceptions import ApiException

from rest_framework.generics import get_object_or_404

from common.utils import get_logger
from common.tree import TreeNode
from assets.models import Account, Asset

from ..const import CloudTypes, Category

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
    def get_kubernetes_data(app_id, username):
        asset = get_object_or_404(Asset, id=app_id)
        account = get_object_or_404(Account, asset=asset, username=username)
        k8s = KubernetesClient(asset.address, account.secret)
        return k8s.get_pods()


class KubernetesTree:
    def __init__(self, tree_id):
        self.tree_id = str(tree_id)

    @staticmethod
    def create_tree_id(pid, tp, v):
        i = dict(parse_qsl(pid))
        i[tp] = v
        tree_id = urlencode(i)
        return tree_id

    def as_tree_node(self, app):
        pid = app.create_app_tree_pid(self.tree_id)
        app_id = str(app.id)
        node = self.create_tree_node(
            app_id, pid, app.name, 'k8s'
        )
        return node

    def as_asset_tree_node(self, asset):
        i = urlencode({'asset_id': self.tree_id})
        node = self.create_tree_node(
            i, str(asset.id), str(asset), 'asset',
        )
        return node

    def as_account_tree_node(self, account, parent_info):
        username = account.username
        name = f'{account.name}({account.username})'
        pid = urlencode({'asset_id': self.tree_id})
        i = self.create_tree_id(pid, 'account', username)
        parent_info.update({'account': username})
        node = self.create_tree_node(
            i, pid, name, 'account', icon='user-tie'
        )
        return node

    def as_namespace_pod_tree_node(self, name, tp, counts=0, is_container=False):
        i = self.create_tree_id(self.tree_id, tp, name)
        name = name if is_container else f'{name}({counts})'
        node = self.create_tree_node(
            i, self.tree_id, name, tp, icon='cloud', is_container=is_container
        )
        return node

    @staticmethod
    def create_tree_node(id_, pid, name, identity, icon='', is_container=False):
        node = {
            'id': id_,
            'name': name,
            'title': name,
            'pId': pid,
            'isParent': not is_container,
            'open': False,
            'iconSkin': icon,
            'meta': {
                'type': 'k8s',
                'data': {
                    'category': Category.CLOUD,
                    'type': CloudTypes.K8S,
                    'identity': identity
                }
            }
        }
        return node

    def async_tree_node(self, parent_info):
        pod_name = parent_info.get('pod')
        asset_id = parent_info.get('asset_id')
        namespace = parent_info.get('namespace')
        account_username = parent_info.get('account')

        tree = []
        data = KubernetesClient.get_kubernetes_data(asset_id, account_username)
        if not data:
            return tree

        if pod_name:
            for container in next(
                    filter(
                        lambda x: x['pod_name'] == pod_name, data[namespace]
                    )
            )['containers']:
                container_node = self.as_namespace_pod_tree_node(
                    container, 'container', is_container=True
                )
                tree.append(container_node)
        elif namespace:
            for pod in data[namespace]:
                pod_nodes = self.as_namespace_pod_tree_node(
                    pod['pod_name'], 'pod', len(pod['containers'])
                )
                tree.append(pod_nodes)
        elif account_username:
            for namespace, pods in data.items():
                namespace_node = self.as_namespace_pod_tree_node(
                    namespace, 'namespace', len(pods)
                )
                tree.append(namespace_node)
        return tree
