# -*- coding: utf-8 -*-
from urllib.parse import urlencode, urlparse

from kubernetes import client
from kubernetes.client import api_client
from kubernetes.client.api import core_v1_api
from sshtunnel import SSHTunnelForwarder, BaseSSHTunnelForwarderError

from common.utils import get_logger
from ..const import CloudTypes, Category

logger = get_logger(__file__)


class KubernetesClient:
    def __init__(self, asset, token):
        self.url = asset.address
        self.token = token or ''
        self.server = self.get_gateway_server(asset)

    @property
    def api(self):
        configuration = client.Configuration()
        scheme = urlparse(self.url).scheme
        if not self.server:
            host = self.url
        else:
            host = f'{scheme}://127.0.0.1:{self.server.local_bind_port}'
        configuration.host = host
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
    def get_gateway_server(asset):
        gateway = None
        if not asset.is_gateway and asset.domain:
            gateway = asset.domain.select_gateway()

        if not gateway:
            return

        remote_bind_address = (
            urlparse(asset.address).hostname,
            urlparse(asset.address).port or 443
        )
        server = SSHTunnelForwarder(
            (gateway.address, gateway.port),
            ssh_username=gateway.username,
            ssh_password=gateway.password,
            ssh_pkey=gateway.private_key_path,
            remote_bind_address=remote_bind_address
        )
        try:
            server.start()
        except BaseSSHTunnelForwarderError:
            err_msg = 'Gateway is not active: %s' % asset.get('name', '')
            print('\033[31m %s \033[0m\n' % err_msg)
        return server

    def run(self, tp, *args):
        func_name = f'get_{tp}s'
        data = []
        if hasattr(self, func_name):
            try:
                data = getattr(self, func_name)(*args)
            except Exception as e:
                logger.error(e)
                raise e

        if self.server:
            self.server.stop()
        return data


class KubernetesTree:
    def __init__(self, asset, secret):
        self.asset = asset
        self.secret = secret

    def as_asset_tree_node(self):
        i = str(self.asset.id)
        name = str(self.asset)
        node = self.create_tree_node(
            i, i, name, 'asset', icon='k8s', is_open=True,
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
        k8s_client = KubernetesClient(self.asset, self.secret)
        if pod:
            tp = 'container'
            containers = k8s_client.run(
                tp, namespace, pod
            )
            for container in containers:
                container_node = self.as_container_tree_node(
                    namespace, pod, container, tp
                )
                tree.append(container_node)
        elif namespace:
            tp = 'pod'
            pods = k8s_client.run(tp, namespace)
            for pod in pods:
                pod_node = self.as_pod_tree_node(namespace, pod, tp)
                tree.append(pod_node)
        else:
            tp = 'namespace'
            namespaces = k8s_client.run(tp)
            for namespace in namespaces:
                namespace_node = self.as_namespace_node(namespace, tp)
                tree.append(namespace_node)
        return tree
