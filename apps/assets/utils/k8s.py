# -*- coding: utf-8 -*-
from urllib.parse import urlencode

from kubernetes import client
from kubernetes.client import api_client
from kubernetes.client.api import core_v1_api
from kubernetes.client.exceptions import ApiException

from common.utils import get_logger
from ..const import CloudTypes, Category

logger = get_logger(__file__)


class KubernetesClient:
    def __init__(self, url, token, proxy=None):
        self.url = url
        self.token = token
        self.proxy = proxy

    @property
    def api(self):
        configuration = client.Configuration()
        configuration.host = self.url
        configuration.proxy = self.proxy
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

    @staticmethod
    def get_proxy_url(asset):
        if not asset.domain:
            return None

        gateway = asset.domain.select_gateway()
        if not gateway:
            return None
        return f'{gateway.address}:{gateway.port}'

    @classmethod
    def run(cls, asset, secret, tp, *args):
        k8s_url = f'{asset.address}'
        proxy_url = cls.get_proxy_url(asset)
        k8s = cls(k8s_url, secret, proxy=proxy_url)
        func_name = f'get_{tp}s'
        data = []
        if hasattr(k8s, func_name):
            try:
                data = getattr(k8s, func_name)(*args)
            except ApiException as e:
                logger.error(e.reason)
        return data


class KubernetesTree:
    def __init__(self, asset, secret):
        self.asset = asset
        self.secret = secret

    def as_asset_tree_node(self):
        i = str(self.asset.id)
        name = str(self.asset)
        node = self.create_tree_node(
            i, i, name, 'asset', is_open=True,
        )
        return node

    def as_namespace_node(self, name, tp):
        i = urlencode({'namespace': name})
        pid = str(self.asset.id)
        node = self.create_tree_node(i, pid, name, tp, icon='cloud')
        return node

    def as_pod_tree_node(self, namespace, name, tp):
        pid = urlencode({'namespace': namespace})
        i = urlencode({'namespace': namespace, 'pod': name})
        node = self.create_tree_node(i, pid, name, tp, icon='cloud')
        return node

    def as_container_tree_node(self, namespace, pod, name, tp):
        pid = urlencode({'namespace': namespace, 'pod': pod})
        i = urlencode({'namespace': namespace, 'pod': pod, 'container': name})
        node = self.create_tree_node(
            i, pid, name, tp, icon='cloud', is_container=True
        )
        return node

    @staticmethod
    def create_tree_node(id_, pid, name, identity, icon='', is_container=False, is_open=False):
        node = {
            'id': id_,
            'name': name,
            'title': name,
            'pId': pid,
            'isParent': not is_container,
            'open': is_open,
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

    def async_tree_node(self, namespace, pod):
        tree = []
        if pod:
            tp = 'container'
            containers = KubernetesClient.run(
                self.asset, self.secret, tp, namespace, pod
            )
            for container in containers:
                container_node = self.as_container_tree_node(
                    namespace, pod, container, tp
                )
                tree.append(container_node)
        elif namespace:
            tp = 'pod'
            pods = KubernetesClient.run(self.asset, self.secret, tp, namespace)
            for pod in pods:
                pod_node = self.as_pod_tree_node(namespace, pod, tp)
                tree.append(pod_node)
        else:
            tp = 'namespace'
            namespaces = KubernetesClient.run(self.asset, self.secret, tp)
            for namespace in namespaces:
                namespace_node = self.as_namespace_node(namespace, tp)
                tree.append(namespace_node)
        return tree
