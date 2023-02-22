# -*- coding: utf-8 -*-
from urllib.parse import urlencode
from urllib3.exceptions import MaxRetryError, LocationParseError

from kubernetes import client
from kubernetes.client import api_client
from kubernetes.client.api import core_v1_api
from kubernetes.client.exceptions import ApiException

from common.utils import get_logger
from common.exceptions import JMSException
from ..const import CloudTypes, Category

logger = get_logger(__file__)


class KubernetesClient:
    def __init__(self, url, token, proxy=None):
        self.url = url
        self.token = token
        self.proxy = proxy

    def get_api(self):
        configuration = client.Configuration()
        configuration.host = self.url
        configuration.proxy = self.proxy
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
        except LocationParseError as e:
            logger.warning("Kubernetes API request url error: {}".format(e))
            raise JMSException(code='k8s_tree_error', detail=e)
        except MaxRetryError:
            msg = "Kubernetes API request timeout"
            logger.warning(msg)
            raise JMSException(code='k8s_tree_error', detail=msg)
        except ApiException as e:
            if e.status == 401:
                msg = "Kubernetes API request unauthorized"
                logger.warning(msg)
            else:
                msg = e
                logger.warning(msg)
            raise JMSException(code='k8s_tree_error', detail=msg)
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

    @classmethod
    def get_proxy_url(cls, asset):
        if not asset.domain:
            return None

        gateway = asset.domain.select_gateway()
        if not gateway:
            return None
        return f'{gateway.address}:{gateway.port}'

    @classmethod
    def get_kubernetes_data(cls, asset, secret):
        k8s_url = f'{asset.address}'
        proxy_url = cls.get_proxy_url(asset)
        k8s = cls(k8s_url, secret, proxy=proxy_url)
        return k8s.get_pods()


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

    def as_namespace_node(self, name, tp, counts=0):
        i = urlencode({'namespace': name})
        pid = str(self.asset.id)
        name = f'{name}({counts})'
        node = self.create_tree_node(i, pid, name, tp, icon='cloud')
        return node

    def as_pod_tree_node(self, namespace, name, tp, counts=0):
        pid = urlencode({'namespace': namespace})
        i = urlencode({'namespace': namespace, 'pod': name})
        name = f'{name}({counts})'
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
        data = KubernetesClient.get_kubernetes_data(self.asset, self.secret)
        if not data:
            return tree

        if pod:
            for container in next(
                    filter(
                        lambda x: x['pod_name'] == pod, data[namespace]
                    )
            )['containers']:
                container_node = self.as_container_tree_node(
                    namespace, pod, container, 'container'
                )
                tree.append(container_node)
        elif namespace:
            for pod in data[namespace]:
                pod_nodes = self.as_pod_tree_node(
                    namespace, pod['pod_name'], 'pod', len(pod['containers'])
                )
                tree.append(pod_nodes)
        else:
            for namespace, pods in data.items():
                namespace_node = self.as_namespace_node(
                    namespace, 'namespace', len(pods)
                )
                tree.append(namespace_node)
        return tree
