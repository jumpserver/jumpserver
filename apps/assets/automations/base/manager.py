import hashlib
import json
import logging
import os
import re
import shutil
import time
from collections import defaultdict
from socket import gethostname

import yaml
from celery import current_task
from celery.worker import state as celery_worker_state
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from premailer import transform

from common.const import Status
from common.db.utils import safe_atomic_db_connection
from common.tasks import send_mail_async
from common.utils import get_logger, lazyproperty, is_openssh_format_key, ssh_pubkey_gen
from libs.ansible.modules_utils.ssh_tunnel import TimeoutSSHTunnelForwarder
from ops.ansible import JMSInventory, DefaultCallback, SuperPlaybookRunner
from ops.ansible.interface import interface
from users.utils import activate_user_language

logger = get_logger(__name__)

BULK_SIZE = 80
RUNTIME_DIR_UNSAFE_CHARS = re.compile(r'[\s/\\:<>|"?*\x00-\x1f]+')


def safe_runtime_dir_name(name):
    dir_name = RUNTIME_DIR_UNSAFE_CHARS.sub('_', str(name or '')).strip('_')
    return dir_name or 'automation'


class SSHTunnelManager:
    def __init__(self, *args, **kwargs):
        self.gateway_servers = dict()
        self.gateway_errors = dict()

    @staticmethod
    def file_to_json(path):
        with open(path, "r") as f:
            d = json.load(f)
        return d

    @staticmethod
    def json_to_file(path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)

    def local_gateway_prepare(self, runner, cancel_callback=None):
        info = self.file_to_json(runner.inventory)
        servers, not_valid = [], []
        servers_by_target = {}
        failed_targets = set()
        failed_target_errors = {}
        host_errors = {}
        gateway_proxy_host = None
        for k, host in info["all"]["hosts"].items():
            if cancel_callback and cancel_callback():
                self.gateway_servers[runner.id] = servers
                return False
            jms_asset, jms_gateway = host.get("jms_asset"), host.get("jms_gateway")
            if not jms_gateway:
                continue
            if gateway_proxy_host is None:
                gateway_proxy_host = interface.get_gateway_proxy_host()

            target_key = (
                str(jms_gateway.get("address")),
                str(jms_gateway.get("port")),
                str(jms_gateway.get("username")),
                str(jms_gateway.get("secret") or ""),
                str(jms_gateway.get("private_key_path") or ""),
                str(jms_asset.get("address")),
                str(jms_asset.get("port")),
                gateway_proxy_host,
            )
            if target_key in failed_targets:
                not_valid.append(k)
                host_errors[k] = failed_target_errors[target_key]
                continue

            try:
                server = servers_by_target.get(target_key)
                if server is None:
                    server = TimeoutSSHTunnelForwarder(
                        (jms_gateway["address"], jms_gateway["port"]),
                        ssh_username=jms_gateway["username"],
                        ssh_password=jms_gateway["secret"],
                        ssh_pkey=jms_gateway["private_key_path"],
                        connect_timeout=settings.SSH_GATEWAY_CONNECT_TIMEOUT,
                        remote_bind_address=(jms_asset["address"], jms_asset["port"]),
                        local_bind_address=(
                            '0.0.0.0' if gateway_proxy_host != '127.0.0.1' else '127.0.0.1',
                            0,
                        ),
                    )
                    server.start()
                    servers_by_target[target_key] = server
                    servers.append(server)
            except Exception as e:
                err_msg = "Gateway is not active: %s" % jms_asset.get("name", "")
                print(f"\033[31m {err_msg} 原因: {e} \033[0m\n")
                failed_targets.add(target_key)
                failed_target_errors[target_key] = f'{err_msg}: {e}'
                host_errors[k] = failed_target_errors[target_key]
                not_valid.append(k)
            else:
                local_bind_port = server.local_bind_port

                host["ansible_host"] = jms_asset["address"] = host["login_host"] = (
                    gateway_proxy_host
                )
                host["ansible_port"] = jms_asset["port"] = host["login_port"] = (
                    local_bind_port
                )

        # 网域不可连接的，就不继续执行此资源的后续任务了
        for a in set(not_valid):
            info["all"]["hosts"].pop(a)
        self.json_to_file(runner.inventory, info)
        self.gateway_servers[runner.id] = servers
        self.gateway_errors[runner.id] = host_errors
        return True

    def get_gateway_errors(self, runner):
        return self.gateway_errors.get(runner.id, {})

    def local_gateway_clean(self, runner):
        servers = self.gateway_servers.pop(runner.id, [])
        self.gateway_errors.pop(runner.id, None)
        for s in servers:
            try:
                s.stop(force=True)
            except Exception:
                pass


class PlaybookCallback(DefaultCallback):
    def playbook_on_stats(self, event_data, **kwargs):
        super().playbook_on_stats(event_data, **kwargs)


class BaseManager:
    def __init__(self, execution):
        self.execution = execution
        self.time_start = time.time()
        self.summary = defaultdict(int)
        self.result = defaultdict(list)
        self.duration = 0
        self.status = Status.success

    def get_assets_group_by_platform(self):
        return self.execution.all_assets_group_by_platform()

    def pre_run(self):
        date_start = timezone.now()
        self.execution.date_start = date_start
        self.execution.status = Status.running
        self.execution.save(update_fields=["date_start", "status"])

        automation = self.execution.automation
        if automation:
            automation.last_execution_date = date_start
            automation.save(update_fields=['last_execution_date'])

    def update_execution(self):
        self.duration = round(time.time() - self.time_start, 2)
        self.execution.date_finished = timezone.now()
        self.execution.duration = self.duration
        self.execution.summary = self.summary
        self.execution.result = self.result
        self.execution.status = self.status
        self.execution.save()

    def print_summary(self):
        content = "\nSummary: \n"
        for k, v in self.summary.items():
            content += f"\t - {k}: {v}\n"
        content += "\t - Using: {}s\n".format(self.duration)
        print(content)

    def get_report_template(self):
        raise NotImplementedError

    def get_report_subject(self):
        return _("Task: {} finished").format(self.execution.automation.name)

    def get_report_context(self):
        return {
            "execution": self.execution,
            "summary": self.execution.summary,
            "result": self.execution.result
        }

    def send_report_if_need(self):
        recipients = self.execution.recipients
        if not recipients:
            return
        print(f"Send report to: {','.join([str(u) for u in recipients])}")
        for user in recipients:
            with activate_user_language(user):
                report = self.gen_report()
                report = transform(report, cssutils_logging_level="CRITICAL")
                subject = self.get_report_subject()
                emails = [user.email]
                send_mail_async(subject, report, emails, html_message=report)

    def gen_report(self):
        template_path = self.get_report_template()
        context = self.get_report_context()
        data = render_to_string(template_path, context)
        return data

    def post_run(self):
        with safe_atomic_db_connection():
            self.update_execution()
            self.print_summary()
            self.send_report_if_need()

    def run(self, *args, **kwargs):
        self.pre_run()
        try:
            self.do_run(*args, **kwargs)
        except Exception as e:
            logging.exception(e)
            self.status = Status.error
        finally:
            self.post_run()

    def do_run(self, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def json_dumps(data):
        return json.dumps(data, indent=4, sort_keys=True)


class PlaybookPrepareMixin:
    bulk_size = BULK_SIZE
    ansible_account_policy = "privileged_first"
    ansible_account_prefer = "root,Administrator"

    summary: dict
    result: dict
    params: dict
    execution = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # example: {'gather_fact_windows': {'id': 'gather_fact_windows', 'name': '', 'method': 'gather_fact', ...} }
        self.method_id_meta_mapper = {
            method["id"]: method
            for method in self.platform_automation_methods
            if method["method"] == self.__class__.method_type()
        }
        # 根据执行方式就行分组, 不同资产的改密、推送等操作可能会使用不同的执行方式
        # 然后根据执行方式分组, 再根据 bulk_size 分组, 生成不同的 playbook
        self.playbooks = []

    @classmethod
    def method_type(cls):
        raise NotImplementedError

    def get_params(self, automation, method_type):
        method_attr = "{}_method".format(method_type)
        method_params = "{}_params".format(method_type)
        method_id = getattr(automation, method_attr)
        automation_params = getattr(automation, method_params)
        serializer = self.method_id_meta_mapper[method_id]["params_serializer"]

        if serializer is None:
            return {}

        data = self.params.get(method_id)
        if not data:
            data = automation_params.get(method_id, {})
        params = serializer(data).data
        return params

    @property
    def platform_automation_methods(self):
        from assets.const import AllTypes
        return AllTypes.get_automation_methods()

    def prepare_runtime_dir(self):
        ansible_dir = settings.ANSIBLE_DIR
        task_name = self.execution.snapshot["name"]
        dir_name = "{}_{}".format(safe_runtime_dir_name(task_name), self.execution.id)
        path = os.path.join(
            ansible_dir,
            "automations",
            self.execution.snapshot["type"],
            dir_name,
            timezone.now().strftime("%Y%m%d_%H%M%S"),
        )
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True, mode=0o700)
        else:
            os.chmod(path, 0o700)
        return path

    def host_callback(self, host, automation=None, **kwargs):
        method_type = self.__class__.method_type()
        host = self.convert_cert_to_file(host, kwargs.get("path_dir"))
        host["params"] = self.get_params(automation, method_type)
        return host

    @staticmethod
    def write_cert_to_file(filename, content):
        with open(filename, "w") as f:
            f.write(content)
        os.chmod(filename, 0o600)
        return filename

    def convert_cert_to_file(self, host, path_dir):
        if not path_dir:
            return host

        specific = host.get("jms_asset", {}).get("secret_info", {})
        cert_fields = ("ca_cert", "client_key", "client_cert")
        filtered = list(filter(lambda x: specific.get(x), cert_fields))
        if not filtered:
            return host

        cert_dir = os.path.join(path_dir, "certs")
        if not os.path.exists(cert_dir):
            os.makedirs(cert_dir, 0o700, True)

        for f in filtered:
            result = self.write_cert_to_file(os.path.join(cert_dir, f), specific.get(f))
            host["jms_asset"]["secret_info"][f] = result

        client_cert = specific.get("client_cert")
        client_key = specific.get("client_key")
        if client_cert and client_key:
            combined = "{}\n{}".format(
                client_cert.rstrip("\n"),
                client_key.lstrip("\n"),
            )
            result = self.write_cert_to_file(
                os.path.join(cert_dir, "client_cert_key.pem"),
                combined,
            )
            host["jms_asset"]["secret_info"]["client_cert_key"] = result
        return host

    @staticmethod
    def generate_public_key(private_key):
        return ssh_pubkey_gen(private_key=private_key, hostname=gethostname())

    @staticmethod
    def generate_private_key_path(secret, path_dir):
        key_name = "." + hashlib.md5(secret.encode("utf-8")).hexdigest()
        key_path = os.path.join(path_dir, key_name)

        if not os.path.exists(key_path):
            # https://github.com/ansible/ansible-runner/issues/544
            # ssh requires OpenSSH format keys to have a full ending newline.
            # It does not require this for old-style PEM keys.
            with open(key_path, "w") as f:
                f.write(secret)
                if is_openssh_format_key(secret.encode("utf-8")):
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
        return dict(inventory.exclude_hosts)

    @lazyproperty
    def runtime_dir(self):
        path = self.prepare_runtime_dir()
        if settings.DEBUG_DEV:
            msg = "Ansible runtime dir: {}".format(path)
            print(msg)
        return path

    @staticmethod
    def generate_playbook(method, sub_playbook_dir):
        method_playbook_dir_path = method["dir"]
        sub_playbook_path = os.path.join(sub_playbook_dir, "project", "main.yml")
        shutil.copytree(method_playbook_dir_path, os.path.dirname(sub_playbook_path))
        if not os.path.exists(sub_playbook_path):
            return None

        with open(sub_playbook_path, "r") as f:
            plays = yaml.safe_load(f)
        for play in plays:
            play["hosts"] = "all"

        with open(sub_playbook_path, "w") as f:
            yaml.safe_dump(plays, f)
        return sub_playbook_path

    def check_automation_enabled(self, platform, assets):
        automation = getattr(platform, 'automation', None)
        if not (automation and getattr(automation, 'ansible_enabled', False)):
            print(_("  - Platform {} ansible disabled").format(platform.name))
            self.on_assets_not_ansible_enabled(assets)
            return False

        automation = platform.automation

        method_type = self.__class__.method_type()
        enabled_attr = "{}_enabled".format(method_type)
        method_attr = "{}_method".format(method_type)

        method_enabled = (
                automation
                and getattr(automation, enabled_attr)
                and getattr(automation, method_attr)
                and getattr(automation, method_attr) in self.method_id_meta_mapper
        )

        if not method_enabled:
            self.on_assets_not_method_enabled(assets, method_type)
            return False
        return True

    def on_assets_not_ansible_enabled(self, assets):
        self.summary["error_assets"] += len(assets)
        self.result["error_assets"].extend([str(asset) for asset in assets])
        for asset in assets:
            print("\t{}".format(asset))

    def on_assets_not_method_enabled(self, assets, method_type):
        self.summary["error_assets"] += len(assets)
        self.result["error_assets"].extend([str(asset) for asset in assets])
        for asset in assets:
            print("\t{}".format(asset))

    def on_playbook_not_found(self, assets):
        print("Playbook generate failed")


class BasePlaybookManager(PlaybookPrepareMixin, BaseManager):
    bulk_size = BULK_SIZE
    ansible_account_policy = "privileged_first"
    ansible_account_prefer = ""

    def __init__(self, execution):
        super().__init__(execution)
        self.params = execution.snapshot.get("params", {})
        self.host_success_callbacks = []
        self.interruption_reason = ''
        self.task_timed_out = False
        self._runner_monitor_last_log = {}
        self._runner_host_labels = {}

    def get_assets_group_by_platform(self):
        return self.execution.all_assets_group_by_platform()

    @classmethod
    def method_type(cls):
        raise NotImplementedError

    def get_runners_by_platform(self, platform, _assets, _index):
        sub_dir = "{}_{}".format(platform.name, _index)
        playbook_dir = os.path.join(self.runtime_dir, sub_dir)
        inventory_path = os.path.join(self.runtime_dir, sub_dir, "hosts.json")

        method_id = getattr(
            platform.automation,
            "{}_method".format(self.__class__.method_type()),
        )
        method = self.method_id_meta_mapper.get(method_id)

        protocol = method.get("protocol")
        inventory_errors = self.generate_inventory(
            _assets, inventory_path, protocol
        )
        for host, error in inventory_errors.items():
            self.on_inventory_host_error(host, error)
        with open(inventory_path, "r") as f:
            inventory_data = json.load(f)
            if not inventory_data["all"].get("hosts"):
                return None, None

        playbook_path = self.generate_playbook(method, playbook_dir)
        if not playbook_path:
            self.on_playbook_not_found(_assets)
            return None, None

        runner = SuperPlaybookRunner(
            inventory_path,
            playbook_path,
            self.runtime_dir,
            callback=PlaybookCallback(),
        )
        return runner, inventory_path

    def get_runners(self):
        assets_group_by_platform = self.get_assets_group_by_platform()
        if settings.DEBUG_DEV:
            msg = "Assets group by platform: {}".format(dict(assets_group_by_platform))
            print(msg)

        runners = []
        available_asset_ids = {
            str(asset.id)
            for assets in assets_group_by_platform.values()
            for asset in assets
        }
        requested_asset_ids = {
            str(asset_id)
            for asset_id in self.execution.snapshot.get("assets", [])
        }
        missing_asset_ids = requested_asset_ids - available_asset_ids
        self.summary["total_assets"] += len(missing_asset_ids)
        for asset_id in sorted(missing_asset_ids):
            self.on_inventory_host_error(
                asset_id, _("Asset not found or inactive")
            )

        for platform, assets in assets_group_by_platform.items():
            self.summary["total_assets"] += len(assets)
            if not assets:
                print("No assets for platform: {}".format(platform.name))
                continue

            if not self.check_automation_enabled(platform, assets):
                print("Platform {} ansible disabled".format(platform.name))
                continue

            # 避免一个任务太大，分批执行
            assets_bulked = [
                assets[i: i + self.bulk_size]
                for i in range(0, len(assets), self.bulk_size)
            ]
            for i, _assets in enumerate(assets_bulked, start=1):
                runner, inventory_path = self.get_runners_by_platform(
                    platform, _assets, i
                )

                if not runner or not inventory_path:
                    continue
                
                runners.append(
                    (
                        runner,
                        {
                            "assets": _assets,
                            "inventory": inventory_path,
                            "platform": platform,
                        },
                    )
                )
        return runners

    def on_host_success(self, host, result):
        self.summary["ok_assets"] += 1
        self.result["ok_assets"].append(host)

        for cb in self.host_success_callbacks:
            cb(host, result)

    def on_host_error(self, host, error, result):
        self.summary["fail_assets"] += 1
        self.result["fail_assets"].append((host, str(error)))
        print(f"\033[31m {host} error: {error} \033[0m\n")

    def _on_host_success(self, host, result, hosts):
        self.on_host_success(host, result.get("ok", ""))

    def _on_host_error(self, host, result, hosts):
        error = hosts.get(host, "")
        detail = result.get("failures", "") or result.get("dark", "")
        self.on_host_error(host, error, detail)

    def on_host_incomplete(self, host, error):
        self.on_host_error(host, error, {})

    def on_inventory_host_error(self, host, error):
        self.summary["fail_assets"] += 1
        self.result["fail_assets"].append((host, str(error)))
        print(f"\033[31m {host} preparation error: {error} \033[0m\n")

    def post_run(self):
        try:
            if self.status not in (Status.canceled, Status.error) and any(
                    self.summary.get(key, 0) > 0
                    for key in (
                        "fail_assets", "fail_accounts",
                        "unverified_accounts",
                    )
            ):
                self.status = Status.failed
            super().post_run()
        finally:
            self.delete_runtime_dir()

    def on_runner_success(self, runner, cb):
        summary = cb.summary
        for state, hosts in summary.items():
            # 错误行为为，host 是 dict， ok 时是 list

            if state == "ok":
                handler = self._on_host_success
            elif state == "skipped":
                continue
            else:
                handler = self._on_host_error

            for host in hosts:
                result = cb.host_results.get(host) or {}
                handler(host, result, hosts)

    @staticmethod
    def is_celery_task_revoked():
        try:
            task_id = current_task.request.id
        except Exception:
            return False
        return bool(task_id and task_id in celery_worker_state.revoked)

    @staticmethod
    def get_inventory_hosts(inventory_path):
        try:
            with open(inventory_path, 'r') as inventory_file:
                inventory = json.load(inventory_file)
        except (OSError, ValueError, TypeError):
            return {}
        return inventory.get('all', {}).get('hosts', {})

    @classmethod
    def get_inventory_host_names(cls, inventory_path):
        return list(cls.get_inventory_hosts(inventory_path).keys())

    def cache_runner_host_labels(self, runner, inventory_path):
        labels = {}
        for host, detail in self.get_inventory_hosts(inventory_path).items():
            asset = detail.get('jms_asset') or {}
            address = asset.get('address') or detail.get('ansible_host')
            labels[host] = (
                f'{host}[{address}]' if address else str(host)
            )
        self._runner_host_labels[str(runner.id)] = labels

    @staticmethod
    def configure_runner_environment(runner):
        task_timeout = int(
            getattr(settings, 'ANSIBLE_AUTOMATION_TASK_TIMEOUT', 300)
            or 0
        )
        if task_timeout > 0:
            runner.envs.setdefault(
                'ANSIBLE_TASK_TIMEOUT', str(task_timeout)
            )

        gateway_timeout = int(
            getattr(settings, 'SSH_GATEWAY_CONNECT_TIMEOUT', 30) or 0
        )
        runner.envs.setdefault(
            'JMS_SSH_GATEWAY_CONNECT_TIMEOUT', str(gateway_timeout)
        )

        remote_client_debug = bool(
            getattr(settings, 'JMS_REMOTE_CLIENT_DEBUG', False)
        )
        runner.envs.setdefault(
            'JMS_REMOTE_CLIENT_DEBUG',
            '1' if remote_client_debug else '0',
        )

    def is_task_deadline_exceeded(self):
        task_timeout = int(
            getattr(settings, 'ANSIBLE_AUTOMATION_TOTAL_TIMEOUT', 21600)
            or 0
        )
        return (
            task_timeout > 0
            and time.time() - self.time_start >= task_timeout
        )

    def mark_task_timed_out(self):
        if self.task_timed_out:
            return
        task_timeout = int(
            getattr(settings, 'ANSIBLE_AUTOMATION_TOTAL_TIMEOUT', 21600)
            or 0
        )
        self.task_timed_out = True
        self.interruption_reason = str(_(
            "Automation task exceeded the maximum runtime of "
            "%(seconds)s seconds"
        )) % {'seconds': task_timeout}
        print(f">>> {self.interruption_reason}")

    def get_waiting_host_groups(
            self, runner, minimum_elapsed=0
    ):
        cb = getattr(runner, 'cb', None)
        if not cb or not hasattr(cb, 'get_running_hosts'):
            return {}

        labels = self._runner_host_labels.get(str(runner.id), {})
        groups = defaultdict(list)
        for host, detail in cb.get_running_hosts().items():
            elapsed = detail.get('elapsed', 0)
            if elapsed < minimum_elapsed:
                continue
            task = detail.get('task') or str(_("Unknown task"))
            label = labels.get(host, str(host))
            groups[task].append((label, elapsed))
        return groups

    @staticmethod
    def format_waiting_host_groups(groups, limit=20):
        messages = []
        for task, hosts in groups.items():
            hosts = sorted(hosts, key=lambda item: item[1], reverse=True)
            shown = hosts[:limit]
            host_text = ', '.join(
                f'{host} ({elapsed}s)' for host, elapsed in shown
            )
            hidden = len(hosts) - len(shown)
            if hidden:
                host_text += str(
                    _(" and %(count)s more")
                ) % {'count': hidden}
            messages.append(f'[{task}] {host_text}')
        return '; '.join(messages)

    def record_stalled_hosts(self, groups):
        if not groups:
            return
        tasks = {
            task: [
                {'host': host, 'waiting_seconds': elapsed}
                for host, elapsed in hosts
            ]
            for task, hosts in groups.items()
        }
        self.result['stalled_hosts'].append({
            'batch': self.summary.get('current_batch'),
            'date': timezone.now().isoformat(),
            'tasks': tasks,
        })

    def persist_waiting_progress(self, groups):
        waiting_hosts = []
        waiting_tasks = {}
        for task, hosts in groups.items():
            labels = [host for host, __ in hosts]
            waiting_hosts.extend(labels)
            waiting_tasks[task] = labels
        self.summary['waiting_hosts'] = waiting_hosts
        self.summary['waiting_tasks'] = waiting_tasks
        self.execution.summary = dict(self.summary)
        try:
            with safe_atomic_db_connection():
                self.execution.save(update_fields=['summary'])
        except Exception:
            logger.exception(
                'Save waiting host progress failed: execution=%s',
                self.execution.id,
            )

    def log_waiting_hosts(self, runner):
        interval = int(
            getattr(settings, 'ANSIBLE_STALL_LOG_INTERVAL', 60) or 0
        )
        if interval <= 0:
            return

        groups = self.get_waiting_host_groups(
            runner, minimum_elapsed=interval
        )
        if not groups:
            return

        runner_id = str(runner.id)
        now = time.monotonic()
        last_log = self._runner_monitor_last_log.get(runner_id, 0)
        if now - last_log < interval:
            return
        self._runner_monitor_last_log[runner_id] = now

        detail = self.format_waiting_host_groups(groups)
        count = sum(len(hosts) for hosts in groups.values())
        print(str(_(
            ">>> Still waiting for %(count)s host(s): %(detail)s"
        )) % {'count': count, 'detail': detail})
        self.persist_waiting_progress(groups)

    def should_cancel_runner(self, runner):
        if self.is_celery_task_revoked():
            self.interruption_reason = str(_("Task canceled by user"))
            return True
        if self.is_task_deadline_exceeded():
            self.mark_task_timed_out()
            return True
        self.log_waiting_hosts(runner)
        return False

    def get_runner_kwargs(self, kwargs, runner):
        run_kwargs = dict(kwargs)
        run_kwargs["clean_workspace"] = False

        job_timeout = int(
            getattr(settings, 'ANSIBLE_RUNNER_JOB_TIMEOUT', 1800) or 0
        )
        if job_timeout > 0:
            run_kwargs.setdefault('timeout', job_timeout)

        idle_timeout = int(
            getattr(settings, 'ANSIBLE_RUNNER_IDLE_TIMEOUT', 900) or 0
        )
        runner_settings = dict(run_kwargs.get('settings') or {})
        if idle_timeout > 0:
            runner_settings.setdefault('idle_timeout', idle_timeout)
        if runner_settings:
            run_kwargs['settings'] = runner_settings

        # Celery uses a threads pool in JumpServer. Threads cannot be force
        # killed reliably, so let ansible-runner poll the worker revoked set
        # and terminate its subprocess cooperatively.
        run_kwargs.setdefault(
            'cancel_callback',
            lambda: self.should_cancel_runner(runner),
        )
        return run_kwargs

    def update_batch_progress(self, completed, total, current=None):
        self.summary['completed_batches'] = completed
        self.summary['total_batches'] = total
        self.summary.pop('waiting_hosts', None)
        self.summary.pop('waiting_tasks', None)
        if current is not None:
            self.summary['current_batch'] = current
        else:
            self.summary.pop('current_batch', None)

        self.execution.summary = dict(self.summary)
        self.execution.result = dict(self.result)
        try:
            with safe_atomic_db_connection():
                self.execution.save(update_fields=['summary', 'result'])
        except Exception:
            logger.exception(
                'Save automation batch progress failed: execution=%s',
                self.execution.id,
            )

    def on_runner_incomplete(
            self, runner, error, inventory=None, assets=None, **kwargs
    ):
        self.interruption_reason = str(error)
        hosts = self.get_inventory_host_names(inventory)
        if hosts:
            cb = getattr(runner, 'cb', None)
            failed_hosts = set()
            if cb:
                for result_key in ('failures', 'dark'):
                    for host, tasks in cb.result.get(
                            result_key, {}
                    ).items():
                        failed_hosts.add(host)
                        task_errors = [
                            detail.get('stderr')
                            or (detail.get('res') or {}).get('msg')
                            or str(error)
                            for detail in tasks.values()
                        ]
                        host_error = '; '.join(
                            item for item in task_errors if item
                        ) or str(error)
                        self.on_host_error(
                            host, host_error, tasks
                        )
            for host in hosts:
                if host in failed_hosts:
                    continue
                self.on_host_incomplete(host, error)
        else:
            assets = assets or []
            self.summary["fail_assets"] += len(assets)
            self.result["fail_assets"].extend(
                [(str(asset), str(error)) for asset in assets]
            )

    @staticmethod
    def _is_nonfatal_runner_timeout(error):
        error_text = str(error)
        return (
            "pexpect.exceptions.TIMEOUT" in error_text
        )

    def on_runner_failed(self, runner, e, assets=None, **kwargs):
        assets = assets or []
        if self._is_nonfatal_runner_timeout(e):
            cb = getattr(runner, "cb", None)
            if cb and cb.finished:
                with safe_atomic_db_connection():
                    self.on_runner_success(runner, cb)
                print("Runner timeout but playbook exited normally, ignore fail mark")
                return True

        waiting = self.get_waiting_host_groups(runner)
        waiting_detail = self.format_waiting_host_groups(waiting)
        self.record_stalled_hosts(waiting)
        error = str(e)
        if waiting_detail:
            error = '{}; {}: {}'.format(
                error, str(_("Hosts still waiting")), waiting_detail
            )

        self.status = (
            Status.error if self.task_timed_out else Status.failed
        )
        self.on_runner_incomplete(
            runner, error, assets=assets, **kwargs
        )
        print("Runner failed: {} {}".format(e, self))
        return False

    def delete_runtime_dir(self):
        if settings.DEBUG_DEV:
            return
        runtime_dir = self.__dict__.get('runtime_dir')
        if runtime_dir:
            shutil.rmtree(runtime_dir, ignore_errors=True)

    def do_run(self, *args, **kwargs):
        print(_(">>> Task preparation phase"), end="\n")
        runners = self.get_runners()
        if len(runners) > 1:
            print(
                _(">>> Executing tasks in batches, total {runner_count}").format(
                    runner_count=len(runners)
                )
            )
        elif len(runners) == 1:
            print(_(">>> Start executing tasks"))
        else:
            print(_(">>> No tasks need to be executed"), end="\n")

        total_runners = len(runners)
        if total_runners:
            self.update_batch_progress(0, total_runners, current=1)

        for i, runner_info in enumerate(runners, start=1):
            if self.is_celery_task_revoked():
                self.status = Status.canceled
                self.interruption_reason = str(_("Task canceled by user"))
                break
            if self.is_task_deadline_exceeded():
                self.mark_task_timed_out()
                self.status = Status.error
                break

            if len(runners) > 1:
                print(_(">>> Begin executing batch {index} of tasks").format(index=i))

            runner, info = runner_info
            ssh_tunnel = SSHTunnelManager()
            self.cache_runner_host_labels(runner, info.get('inventory'))
            self.configure_runner_environment(runner)

            try:
                gateway_ready = ssh_tunnel.local_gateway_prepare(
                    runner,
                    cancel_callback=lambda: self.should_cancel_runner(runner),
                )
                if not gateway_ready:
                    self.status = (
                        Status.error
                        if self.task_timed_out
                        else Status.canceled
                    )
                    break
                for host, error in ssh_tunnel.get_gateway_errors(
                        runner
                ).items():
                    self.on_host_error(host, error, {})
                cb = runner.run(**self.get_runner_kwargs(kwargs, runner))
                runner_interrupted = (
                    not cb.finished
                    or cb.status in (
                        Status.canceled,
                        'timeout',
                        'unknown',
                        'running',
                    )
                )
                if runner_interrupted:
                    reason = (
                        self.interruption_reason
                        or str(_(
                            "Ansible runner stopped before completing "
                            "the batch: %(status)s"
                        )) % {'status': cb.status}
                    )
                    waiting = self.get_waiting_host_groups(runner)
                    waiting_detail = self.format_waiting_host_groups(
                        waiting
                    )
                    self.record_stalled_hosts(waiting)
                    if waiting_detail:
                        reason = '{}; {}: {}'.format(
                            reason,
                            str(_("Hosts still waiting")),
                            waiting_detail,
                        )
                    print(f">>> {reason}")
                    self.on_runner_incomplete(runner, reason, **info)
                    if cb.status == Status.canceled:
                        self.status = (
                            Status.error
                            if self.task_timed_out
                            else Status.canceled
                        )
                        break
                    self.status = Status.failed
                else:
                    with safe_atomic_db_connection():
                        self.on_runner_success(runner, cb)
            except Exception as e:
                self.on_runner_failed(runner, e, **info)
            finally:
                ssh_tunnel.local_gateway_clean(runner)
                print("\n")

            next_batch = i + 1 if i < total_runners else None
            self.update_batch_progress(i, total_runners, current=next_batch)
