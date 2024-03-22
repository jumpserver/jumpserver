import hashlib
import json
import os
import shutil
from socket import gethostname

import yaml
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from sshtunnel import SSHTunnelForwarder

from assets.automations.methods import platform_automation_methods
from common.utils import get_logger, lazyproperty, is_openssh_format_key, ssh_pubkey_gen
from ops.ansible import JMSInventory, SuperPlaybookRunner, DefaultCallback

logger = get_logger(__name__)


class SSHTunnelManager:
    def __init__(self, *args, **kwargs):
        self.gateway_servers = dict()

    @staticmethod
    def file_to_json(path):
        with open(path, 'r') as f:
            d = json.load(f)
        return d

    @staticmethod
    def json_to_file(path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)

    def local_gateway_prepare(self, runner):
        info = self.file_to_json(runner.inventory)
        servers, not_valid = [], []
        for k, host in info['all']['hosts'].items():
            jms_asset, jms_gateway = host.get('jms_asset'), host.get('gateway')
            if not jms_gateway:
                continue
            try:
                server = SSHTunnelForwarder(
                    (jms_gateway['address'], jms_gateway['port']),
                    ssh_username=jms_gateway['username'],
                    ssh_password=jms_gateway['secret'],
                    ssh_pkey=jms_gateway['private_key_path'],
                    remote_bind_address=(jms_asset['address'], jms_asset['port'])
                )
                server.start()
            except Exception as e:
                err_msg = 'Gateway is not active: %s' % jms_asset.get('name', '')
                print(f'\033[31m {err_msg} 原因: {e} \033[0m\n')
                not_valid.append(k)
            else:
                local_bind_port = server.local_bind_port
                host['ansible_host'] = jms_asset['address'] = host['login_host'] = '127.0.0.1'
                host['ansible_port'] = jms_asset['port'] = host['login_port'] = local_bind_port
                servers.append(server)

        # 网域不可连接的，就不继续执行此资源的后续任务了
        for a in set(not_valid):
            info['all']['hosts'].pop(a)
        self.json_to_file(runner.inventory, info)
        self.gateway_servers[runner.id] = servers

    def local_gateway_clean(self, runner):
        servers = self.gateway_servers.get(runner.id, [])
        for s in servers:
            try:
                s.stop()
            except Exception:
                pass


class PlaybookCallback(DefaultCallback):
    def playbook_on_stats(self, event_data, **kwargs):
        super().playbook_on_stats(event_data, **kwargs)


class BasePlaybookManager:
    bulk_size = 100
    ansible_account_policy = 'privileged_first'
    ansible_account_prefer = 'root,Administrator'

    def __init__(self, execution):
        self.execution = execution
        self.method_id_meta_mapper = {
            method['id']: method
            for method in self.platform_automation_methods
            if method['method'] == self.__class__.method_type()
        }
        # 根据执行方式就行分组, 不同资产的改密、推送等操作可能会使用不同的执行方式
        # 然后根据执行方式分组, 再根据 bulk_size 分组, 生成不同的 playbook
        self.playbooks = []
        params = self.execution.snapshot.get('params')
        self.params = params or {}

    def get_params(self, automation, method_type):
        method_attr = '{}_method'.format(method_type)
        method_params = '{}_params'.format(method_type)
        method_id = getattr(automation, method_attr)
        automation_params = getattr(automation, method_params)
        serializer = self.method_id_meta_mapper[method_id]['params_serializer']

        if serializer is None:
            return {}

        data = self.params.get(method_id)
        if not data:
            data = automation_params.get(method_id, {})
        params = serializer(data).data
        return {
            field_name: automation_params.get(field_name, '')
            if not params[field_name] else params[field_name]
            for field_name in params
        }

    @property
    def platform_automation_methods(self):
        return platform_automation_methods

    @classmethod
    def method_type(cls):
        raise NotImplementedError

    def get_assets_group_by_platform(self):
        return self.execution.all_assets_group_by_platform()

    def prepare_runtime_dir(self):
        ansible_dir = settings.ANSIBLE_DIR
        task_name = self.execution.snapshot['name']
        dir_name = '{}_{}'.format(task_name.replace(' ', '_'), self.execution.id)
        path = os.path.join(
            ansible_dir, 'automations', self.execution.snapshot['type'],
            dir_name, timezone.now().strftime('%Y%m%d_%H%M%S')
        )
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True, mode=0o755)
        return path

    @lazyproperty
    def runtime_dir(self):
        path = self.prepare_runtime_dir()
        if settings.DEBUG_DEV:
            msg = 'Ansible runtime dir: {}'.format(path)
            print(msg)
        return path

    @staticmethod
    def write_cert_to_file(filename, content):
        with open(filename, 'w') as f:
            f.write(content)
        return filename

    def convert_cert_to_file(self, host, path_dir):
        if not path_dir:
            return host

        specific = host.get('jms_asset', {}).get('secret_info', {})
        cert_fields = ('ca_cert', 'client_key', 'client_cert')
        filtered = list(filter(lambda x: specific.get(x), cert_fields))
        if not filtered:
            return host

        cert_dir = os.path.join(path_dir, 'certs')
        if not os.path.exists(cert_dir):
            os.makedirs(cert_dir, 0o700, True)

        for f in filtered:
            result = self.write_cert_to_file(
                os.path.join(cert_dir, f), specific.get(f)
            )
            host['jms_asset']['secret_info'][f] = result
        return host

    def host_callback(self, host, automation=None, **kwargs):
        method_type = self.__class__.method_type()
        enabled_attr = '{}_enabled'.format(method_type)
        method_attr = '{}_method'.format(method_type)

        method_enabled = automation and \
                         getattr(automation, enabled_attr) and \
                         getattr(automation, method_attr) and \
                         getattr(automation, method_attr) in self.method_id_meta_mapper

        if not method_enabled:
            host['error'] = _('{} disabled'.format(self.__class__.method_type()))
            return host

        host = self.convert_cert_to_file(host, kwargs.get('path_dir'))
        host['params'] = self.get_params(automation, method_type)
        return host

    @staticmethod
    def generate_public_key(private_key):
        return ssh_pubkey_gen(private_key=private_key, hostname=gethostname())

    @staticmethod
    def generate_private_key_path(secret, path_dir):
        key_name = '.' + hashlib.md5(secret.encode('utf-8')).hexdigest()
        key_path = os.path.join(path_dir, key_name)

        if not os.path.exists(key_path):
            # https://github.com/ansible/ansible-runner/issues/544
            # ssh requires OpenSSH format keys to have a full ending newline.
            # It does not require this for old-style PEM keys.
            with open(key_path, 'w') as f:
                f.write(secret)
                if is_openssh_format_key(secret.encode('utf-8')):
                    f.write("\n")
            os.chmod(key_path, 0o400)
        return key_path

    def generate_inventory(self, platformed_assets, inventory_path, protocol):
        inventory = JMSInventory(
            assets=platformed_assets,
            account_prefer=self.ansible_account_prefer,
            account_policy=self.ansible_account_policy,
            host_callback=self.host_callback,
            task_type=self.__class__.method_type(),
            protocol=protocol,
        )
        inventory.write_to_file(inventory_path)

    @staticmethod
    def generate_playbook(method, sub_playbook_dir):
        method_playbook_dir_path = method['dir']
        sub_playbook_path = os.path.join(sub_playbook_dir, 'project', 'main.yml')
        shutil.copytree(method_playbook_dir_path, os.path.dirname(sub_playbook_path))

        with open(sub_playbook_path, 'r') as f:
            plays = yaml.safe_load(f)
        for play in plays:
            play['hosts'] = 'all'

        with open(sub_playbook_path, 'w') as f:
            yaml.safe_dump(plays, f)
        return sub_playbook_path

    def get_runners(self):
        assets_group_by_platform = self.get_assets_group_by_platform()
        if settings.DEBUG_DEV:
            msg = 'Assets group by platform: {}'.format(dict(assets_group_by_platform))
            print(msg)
        runners = []
        for platform, assets in assets_group_by_platform.items():
            if not assets:
                continue
            if not platform.automation or not platform.automation.ansible_enabled:
                print(_("  - Platform {} ansible disabled").format(platform.name))
                continue
            assets_bulked = [assets[i:i + self.bulk_size] for i in range(0, len(assets), self.bulk_size)]

            for i, _assets in enumerate(assets_bulked, start=1):
                sub_dir = '{}_{}'.format(platform.name, i)
                playbook_dir = os.path.join(self.runtime_dir, sub_dir)
                inventory_path = os.path.join(self.runtime_dir, sub_dir, 'hosts.json')

                method_id = getattr(platform.automation, '{}_method'.format(self.__class__.method_type()))
                method = self.method_id_meta_mapper.get(method_id)

                if not method:
                    logger.error("Method not found: {}".format(method_id))
                    continue
                protocol = method.get('protocol')
                self.generate_inventory(_assets, inventory_path, protocol)
                playbook_path = self.generate_playbook(method, playbook_dir)
                if not playbook_path:
                    continue

                runer = SuperPlaybookRunner(
                    inventory_path,
                    playbook_path,
                    self.runtime_dir,
                    callback=PlaybookCallback(),
                )

                with open(inventory_path, 'r') as f:
                    inventory_data = json.load(f)
                    if not inventory_data['all'].get('hosts'):
                        continue

                runners.append(runer)
        return runners

    def on_host_success(self, host, result):
        pass

    def on_host_error(self, host, error, result):
        if settings.DEBUG_DEV:
            print('host error: {} -> {}'.format(host, error))

    def on_runner_success(self, runner, cb):
        summary = cb.summary
        for state, hosts in summary.items():
            for host in hosts:
                result = cb.host_results.get(host)
                if state == 'ok':
                    self.on_host_success(host, result)
                elif state == 'skipped':
                    pass
                else:
                    error = hosts.get(host)
                    self.on_host_error(host, error, result)

    def on_runner_failed(self, runner, e):
        print("Runner failed: {} {}".format(e, self))

    @staticmethod
    def json_dumps(data):
        return json.dumps(data, indent=4, sort_keys=True)

    def delete_runtime_dir(self):
        if settings.DEBUG_DEV:
            return
        shutil.rmtree(self.runtime_dir)

    def run(self, *args, **kwargs):
        print(">>> 任务准备阶段\n")
        runners = self.get_runners()
        if len(runners) > 1:
            print("### 分次执行任务, 总共 {}\n".format(len(runners)))
        elif len(runners) == 1:
            print(">>> 开始执行任务\n")
        else:
            print("### 没有需要执行的任务\n")

        self.execution.date_start = timezone.now()
        for i, runner in enumerate(runners, start=1):
            if len(runners) > 1:
                print(">>> 开始执行第 {} 批任务".format(i))
            ssh_tunnel = SSHTunnelManager()
            ssh_tunnel.local_gateway_prepare(runner)
            try:
                cb = runner.run(**kwargs)
                self.on_runner_success(runner, cb)
            except Exception as e:
                self.on_runner_failed(runner, e)
            finally:
                ssh_tunnel.local_gateway_clean(runner)
                print('\n')
        self.execution.status = 'success'
        self.execution.date_finished = timezone.now()
        self.execution.save()
        self.delete_runtime_dir()
