import hashlib
import json
import os
import shutil
import time
from collections import defaultdict
from socket import gethostname

import yaml
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from premailer import transform
from sshtunnel import SSHTunnelForwarder

from assets.automations.methods import platform_automation_methods
from common.const import Status
from common.db.utils import safe_db_connection
from common.tasks import send_mail_async
from common.utils import get_logger, lazyproperty, is_openssh_format_key, ssh_pubkey_gen
from ops.ansible import JMSInventory, DefaultCallback, SuperPlaybookRunner
from ops.ansible.interface import interface

logger = get_logger(__name__)


class SSHTunnelManager:
    def __init__(self, *args, **kwargs):
        self.gateway_servers = dict()

    @staticmethod
    def file_to_json(path):
        with open(path, "r") as f:
            d = json.load(f)
        return d

    @staticmethod
    def json_to_file(path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)

    def local_gateway_prepare(self, runner):
        info = self.file_to_json(runner.inventory)
        servers, not_valid = [], []
        for k, host in info["all"]["hosts"].items():
            jms_asset, jms_gateway = host.get("jms_asset"), host.get("jms_gateway")
            if not jms_gateway:
                continue
            try:
                server = SSHTunnelForwarder(
                    (jms_gateway["address"], jms_gateway["port"]),
                    ssh_username=jms_gateway["username"],
                    ssh_password=jms_gateway["secret"],
                    ssh_pkey=jms_gateway["private_key_path"],
                    remote_bind_address=(jms_asset["address"], jms_asset["port"]),
                )
                server.start()
            except Exception as e:
                err_msg = "Gateway is not active: %s" % jms_asset.get("name", "")
                print(f"\033[31m {err_msg} 原因: {e} \033[0m\n")
                not_valid.append(k)
            else:
                local_bind_port = server.local_bind_port

                host["ansible_host"] = jms_asset["address"] = host["login_host"] = (
                    interface.get_gateway_proxy_host()
                )
                host["ansible_port"] = jms_asset["port"] = host["login_port"] = (
                    local_bind_port
                )
                servers.append(server)

        # 网域不可连接的，就不继续执行此资源的后续任务了
        for a in set(not_valid):
            info["all"]["hosts"].pop(a)
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
        self.execution.date_start = timezone.now()
        self.execution.status = Status.running
        self.execution.save(update_fields=["date_start", "status"])

    def update_execution(self):
        self.duration = int(time.time() - self.time_start)
        self.execution.date_finished = timezone.now()
        self.execution.duration = self.duration
        self.execution.summary = self.summary
        self.execution.result = self.result
        self.execution.status = self.status

        with safe_db_connection():
            self.execution.save()

    def print_summary(self):
        content = "\nSummery: \n"
        for k, v in self.summary.items():
            content += f"\t - {k}: {v}\n"
        content += "\t - Using: {}s\n".format(self.duration)
        print(content)

    def get_report_template(self):
        raise NotImplementedError

    def get_report_subject(self):
        return f"Automation {self.execution.id} finished"

    def get_report_context(self):
        return {
            "execution": self.execution,
            "summary": self.execution.summary,
            "result": self.execution.result,
        }

    def send_report_if_need(self):
        recipients = self.execution.recipients
        if not recipients:
            return
        print("Send report to: ",  ",".join([str(u) for u in recipients]))

        report = self.gen_report()
        report = transform(report)
        subject = self.get_report_subject()
        emails = [r.email for r in recipients if r.email]
        send_mail_async(subject, report, emails, html_message=report)

    def gen_report(self):
        template_path = self.get_report_template()
        context = self.get_report_context()
        data = render_to_string(template_path, context)
        return data

    def post_run(self):
        self.update_execution()
        self.print_summary()
        self.send_report_if_need()

    def run(self, *args, **kwargs):
        self.pre_run()
        try:
            self.do_run(*args, **kwargs)
        except:
            self.status = 'error'
        finally:
            self.post_run()

    def do_run(self, *args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def json_dumps(data):
        return json.dumps(data, indent=4, sort_keys=True)


class PlaybookPrepareMixin:
    bulk_size = 100
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
        return platform_automation_methods

    def prepare_runtime_dir(self):
        ansible_dir = settings.ANSIBLE_DIR
        task_name = self.execution.snapshot["name"]
        dir_name = "{}_{}".format(task_name.replace(" ", "_"), self.execution.id)
        path = os.path.join(
            ansible_dir,
            "automations",
            self.execution.snapshot["type"],
            dir_name,
            timezone.now().strftime("%Y%m%d_%H%M%S"),
        )
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True, mode=0o755)
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

        with open(sub_playbook_path, "r") as f:
            plays = yaml.safe_load(f)
        for play in plays:
            play["hosts"] = "all"

        with open(sub_playbook_path, "w") as f:
            yaml.safe_dump(plays, f)
        return sub_playbook_path

    def check_automation_enabled(self, platform, assets):
        if not platform.automation or not platform.automation.ansible_enabled:
            print(_("  - Platform {} ansible disabled").format(platform.name))
            self.on_assets_not_ansible_enabled(assets)

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
    bulk_size = 100
    ansible_account_policy = "privileged_first"
    ansible_account_prefer = "root,Administrator"

    def __init__(self, execution):
        super().__init__(execution)
        self.params = execution.snapshot.get("params", {})
        self.host_success_callbacks = []

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
        self.generate_inventory(_assets, inventory_path, protocol)
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
                assets[i : i + self.bulk_size]
                for i in range(0, len(assets), self.bulk_size)
            ]
            for i, _assets in enumerate(assets_bulked, start=1):
                runner, inventory_path = self.get_runners_by_platform(
                    platform, _assets, i
                )

                if not runner or not inventory_path:
                    continue

                with open(inventory_path, "r") as f:
                    inventory_data = json.load(f)
                    if not inventory_data["all"].get("hosts"):
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

    def post_run(self):
        if self.summary['fail_assets']:
            self.status = 'failed'
        super().post_run()

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
                result = cb.host_results.get(host)
                handler(host, result, hosts)

    def on_runner_failed(self, runner, e, assets=None, **kwargs):
        self.summary["fail_assets"] += len(assets)
        self.result["fail_assets"].extend(
            [(str(asset), str("e")[:10]) for asset in assets]
        )
        print("Runner failed: {} {}".format(e, self))

    def delete_runtime_dir(self):
        if settings.DEBUG_DEV:
            return
        shutil.rmtree(self.runtime_dir, ignore_errors=True)

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

        for i, runner_info in enumerate(runners, start=1):
            if len(runners) > 1:
                print(_(">>> Begin executing batch {index} of tasks").format(index=i))

            runner, info = runner_info
            ssh_tunnel = SSHTunnelManager()
            ssh_tunnel.local_gateway_prepare(runner)

            try:
                kwargs.update({"clean_workspace": False})
                cb = runner.run(**kwargs)
                self.on_runner_success(runner, cb)
            except Exception as e:
                self.on_runner_failed(runner, e, **info)
            finally:
                ssh_tunnel.local_gateway_clean(runner)
                print("\n")
