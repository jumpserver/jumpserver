# -*- coding: utf-8 -*-


from tempfile import NamedTemporaryFile
import os.path

from ansible.inventory.group import Group
from ansible.inventory.host import Host
from ansible.inventory import Inventory
from ansible.runner import Runner
from ansible.playbook import PlayBook
from ansible import callbacks
from ansible import utils
import ansible.constants as C
from passlib.hash import sha512_crypt
from django.template.loader import get_template
from django.template import Context


from jumpserver.api import logger


API_DIR = os.path.dirname(os.path.abspath(__file__))
ANSIBLE_DIR = os.path.join(API_DIR, 'playbooks')
C.HOST_KEY_CHECKING = False


class AnsibleError(StandardError):
    """
    the base AnsibleError which contains error(required),
    data(optional) and message(optional).
    存储所有Ansible 异常对象
    """
    def __init__(self, error, data='', message=''):
        super(AnsibleError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message


class CommandValueError(AnsibleError):
    """
    indicate the input value has error or invalid. 
    the data specifies the error field of input form.
    输入不合法 异常对象
    """
    def __init__(self, field, message=''):
        super(CommandValueError, self).__init__('value:invalid', field, message)


class MyInventory(Inventory):
    """
    this is my ansible inventory object.
    """
    def __init__(self, resource):
        """
        resource的数据格式是一个列表字典，比如
            {
                "group1": {
                    "hosts": [{"hostname": "10.10.10.10", "port": "22", "username": "test", "password": "mypass"}, ...],
                    "vars": {"var1": value1, "var2": value2, ...}
                }
            }

        如果你只传入1个列表，这默认该列表内的所有主机属于my_group组,比如
            [{"hostname": "10.10.10.10", "port": "22", "username": "test", "password": "mypass"}, ...]
        """
        self.resource = resource
        self.inventory = Inventory(host_list=[])
        self.gen_inventory()

    def my_add_group(self, hosts, groupname, groupvars=None):
        """
        add hosts to a group
        """
        my_group = Group(name=groupname)

        # if group variables exists, add them to group
        if groupvars:
            for key, value in groupvars.iteritems():
                my_group.set_variable(key, value)

        # add hosts to group
        for host in hosts:
            # set connection variables
            hostname = host.get("hostname")
            hostip = host.get('ip', hostname)
            hostport = host.get("port")
            username = host.get("username")
            password = host.get("password")
            ssh_key = host.get("ssh_key")
            my_host = Host(name=hostname, port=hostport)
            my_host.set_variable('ansible_ssh_host', hostip)
            my_host.set_variable('ansible_ssh_port', hostport)
            my_host.set_variable('ansible_ssh_user', username)
            my_host.set_variable('ansible_ssh_pass', password)
            my_host.set_variable('ansible_ssh_private_key_file', ssh_key)

            # set other variables 
            for key, value in host.iteritems():
                if key not in ["hostname", "port", "username", "password"]:
                    my_host.set_variable(key, value)
            # add to group
            my_group.add_host(my_host)

        self.inventory.add_group(my_group)

    def gen_inventory(self):
        """
        add hosts to inventory.
        """
        if isinstance(self.resource, list):
            self.my_add_group(self.resource, 'default_group')
        elif isinstance(self.resource, dict):
            for groupname, hosts_and_vars in self.resource.iteritems():
                self.my_add_group(hosts_and_vars.get("hosts"), groupname, hosts_and_vars.get("vars"))


class MyRunner(MyInventory):
    """
    This is a General object for parallel execute modules.
    """
    def __init__(self, *args, **kwargs):
        super(MyRunner, self).__init__(*args, **kwargs)
        self.results_raw = {}

    def run(self, module_name='shell', module_args='', timeout=10, forks=10, pattern='*',
            become=False, become_method='sudo', become_user='root', become_pass='', transport='paramiko'):
        """
        run module from andible ad-hoc.
        module_name: ansible module_name
        module_args: ansible module args
        """
        hoc = Runner(module_name=module_name,
                     module_args=module_args,
                     timeout=timeout,
                     inventory=self.inventory,
                     pattern=pattern,
                     forks=forks,
                     become=become,
                     become_method=become_method,
                     become_user=become_user,
                     become_pass=become_pass,
                     transport=transport
                     )
        self.results_raw = hoc.run()
        logger.debug(self.results_raw)
        return self.results_raw

    @property
    def results(self):
        """
        {'failed': {'localhost': ''}, 'ok': {'jumpserver': ''}}
        """
        result = {'failed': {}, 'ok': {}}
        dark = self.results_raw.get('dark')
        contacted = self.results_raw.get('contacted')
        if dark:
            for host, info in dark.items():
                result['failed'][host] = info.get('msg')

        if contacted:
            for host, info in contacted.items():
                if info.get('invocation').get('module_name') in ['raw', 'shell', 'command', 'script']:
                    if info.get('rc') == 0:
                        result['ok'][host] = info.get('stdout') + info.get('stderr')
                    else:
                        result['failed'][host] = info.get('stdout') + info.get('stderr')
                else:
                    if info.get('failed'):
                        result['failed'][host] = info.get('msg')
                    else:
                        result['ok'][host] = info.get('changed')
        return result


class Command(MyInventory):
    """
    this is a command object for parallel execute command.
    """
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.results_raw = {}

    def run(self, command, module_name="command", timeout=10, forks=10, pattern=''):
        """
        run command from andible ad-hoc.
        command  : 必须是一个需要执行的命令字符串， 比如 
                 'uname -a'
        """
        data = {}

        if module_name not in ["raw", "command", "shell"]:
            raise CommandValueError("module_name",
                                    "module_name must be of the 'raw, command, shell'")
        hoc = Runner(module_name=module_name,
                     module_args=command,
                     timeout=timeout,
                     inventory=self.inventory,
                     pattern=pattern,
                     forks=forks,
                     )
        self.results_raw = hoc.run()

    @property
    def result(self):
        result = {}
        for k, v in self.results_raw.items():
            if k == 'dark':
                for host, info in v.items():
                    result[host] = {'dark': info.get('msg')}
            elif k == 'contacted':
                for host, info in v.items():
                    result[host] = {}
                    if info.get('stdout'):
                        result[host]['stdout'] = info.get('stdout')
                    elif info.get('stderr'):
                        result[host]['stderr'] = info.get('stderr')
        return result

    @property
    def state(self):
        result = {}
        if self.stdout:
            result['ok'] = self.stdout
        if self.stderr:
            result['err'] = self.stderr
        if self.dark:
            result['dark'] = self.dark
        return result

    @property
    def exec_time(self):
        """
        get the command execute time.
        """
        result = {}
        all = self.results_raw.get("contacted")
        for key, value in all.iteritems():
            result[key] = {
                    "start": value.get("start"),
                    "end"  : value.get("end"),
                    "delta": value.get("delta"),}
        return result

    @property
    def stdout(self):
        """
        get the comamnd standard output.
        """
        result = {}
        all = self.results_raw.get("contacted")
        for key, value in all.iteritems():
            result[key] = value.get("stdout")
        return result

    @property
    def stderr(self):
        """
        get the command standard error.
        """
        result = {}
        all = self.results_raw.get("contacted")
        for key, value in all.iteritems():
            if value.get("stderr") or value.get("warnings"):
                result[key] = {
                    "stderr": value.get("stderr"),
                    "warnings": value.get("warnings"),}
        return result

    @property
    def dark(self):
        """
        get the dark results.
        """
        return self.results_raw.get("dark")


class MyTask(MyRunner):
    """
    this is a tasks object for include the common command.
    """
    def __init__(self, *args, **kwargs):
        super(MyTask, self).__init__(*args, **kwargs)

    def push_key(self, user, key_path):
        """
        push the ssh authorized key to target.
        """
        module_args = 'user="%s" key="{{ lookup("file", "%s") }}" state=present' % (user, key_path)
        self.run("authorized_key", module_args, become=True)

        return self.results

    def push_multi_key(self, **user_info):
        """
        push multi key
        :param user_info:
        :return:
        """
        ret_failed = []
        ret_success = []
        for user, key_path in user_info.iteritems():
            ret = self.push_key(user, key_path)
            if ret.get("status") == "ok":
                ret_success.append(ret)
            if ret.get("status") == "failed":
                ret_failed.append(ret)

        if ret_failed:
            return {"status": "failed", "msg": ret_failed}
        else:
            return {"status": "success", "msg": ret_success}

    def del_key(self, user, key_path):
        """
        push the ssh authorized key to target.
        """
        if user == 'root':
            return {"status": "failed", "msg": "root cann't be delete"}
        module_args = 'user="%s" key="{{ lookup("file", "%s") }}" state="absent"' % (user, key_path)
        self.run("authorized_key", module_args, become=True)

        return self.results

    def add_user(self, username, password=''):
        """
        add a host user.
        """

        if password:
            encrypt_pass = sha512_crypt.encrypt(password)
            module_args = 'name=%s shell=/bin/bash password=%s' % (username, encrypt_pass)
        else:
            module_args = 'name=%s shell=/bin/bash' % username

        self.run("user", module_args, become=True)

        return self.results

    def add_multi_user(self, **user_info):
        """
        add multi user
        :param user_info: keyword args
            {username: password}
        :return:
        """
        ret_success = []
        ret_failed = []
        for user, password in user_info.iteritems():
            ret = self.add_user(user, password)
            if ret.get("status") == "ok":
                ret_success.append(ret)
            if ret.get("status") == "failed":
                ret_failed.append(ret)

        if ret_failed:
            return {"status": "failed", "msg": ret_failed}
        else:
            return {"status": "success", "msg": ret_success}

    def del_user(self, username):
        """
        delete a host user.
        """
        if username == 'root':
            return {"status": "failed", "msg": "root cann't be delete"}
        module_args = 'name=%s state=absent remove=yes move_home=yes force=yes' % username
        self.run("user", module_args, become=True)
        return self.results

    def del_user_sudo(self, username):
        """
        delete a role sudo item
        :param username:
        :return:
        """
        if username == 'root':
            return {"status": "failed", "msg": "root cann't be delete"}
        module_args = "sed -i 's/^%s.*//' /etc/sudoers" % username
        self.run("command", module_args, become=True)
        return self.results

    @staticmethod
    def gen_sudo_script(role_list, sudo_list):
        # receive role_list = [role1, role2] sudo_list = [sudo1, sudo2]
        # return sudo_alias={'NETWORK': '/sbin/ifconfig, /ls'} sudo_user={'user1': ['NETWORK', 'SYSTEM']}
        sudo_alias = {}
        sudo_user = {}
        for sudo in sudo_list:
            sudo_alias[sudo.name] = sudo.commands

        for role in role_list:
            sudo_user[role.name] = ','.join(sudo_alias.keys())

        sudo_j2 = get_template('jperm/role_sudo.j2')
        sudo_content = sudo_j2.render(Context({"sudo_alias": sudo_alias, "sudo_user": sudo_user}))
        sudo_file = NamedTemporaryFile(delete=False)
        sudo_file.write(sudo_content)
        sudo_file.close()
        return sudo_file.name

    def push_sudo_file(self, role_list, sudo_list):
        """
        use template to render pushed sudoers file
        :return:
        """
        module_args1 = self.gen_sudo_script(role_list, sudo_list)
        self.run("script", module_args1, become=True)
        return self.results

    def recyle_cmd_alias(self, role_name):
        """
        recyle sudo cmd alias
        :return:
        """
        if role_name == 'root':
            return {"status": "failed", "msg": "can't recyle root privileges"}
        module_args = "sed -i 's/^%s.*//' /etc/sudoers" % role_name
        self.run("command", module_args, become=True)
        return self.results


class CustomAggregateStats(callbacks.AggregateStats):
    """                                                                             
    Holds stats about per-host activity during playbook runs.                       
    """
    def __init__(self):
        super(CustomAggregateStats, self).__init__()
        self.results = []

    def compute(self, runner_results, setup=False, poll=False,
                ignore_errors=False):
        """                                                                         
        Walk through all results and increment stats.                               
        """
        super(CustomAggregateStats, self).compute(runner_results, setup, poll,
                                              ignore_errors)

        self.results.append(runner_results)

    def summarize(self, host):
        """                                                                         
        Return information about a particular host                                  
        """
        summarized_info = super(CustomAggregateStats, self).summarize(host)

        # Adding the info I need                                                    
        summarized_info['result'] = self.results

        return summarized_info


class MyPlaybook(MyInventory):
    """
    this is my playbook object for execute playbook.
    """
    def __init__(self, *args, **kwargs):
        super(MyPlaybook, self).__init__(*args, **kwargs)

    def run(self, playbook_relational_path, extra_vars=None):
        """
        run ansible playbook,
        only surport relational path.
        """
        stats = callbacks.AggregateStats()
        playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
        runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)
        playbook_path = os.path.join(ANSIBLE_DIR, playbook_relational_path)

        pb = PlayBook(
            playbook=playbook_path,
            stats=stats,
            callbacks=playbook_cb,
            runner_callbacks=runner_cb,
            inventory=self.inventory,
            extra_vars=extra_vars,
            check=False)

        self.results = pb.run()

    @property
    def raw_results(self):
        """
        get the raw results after playbook run.
        """
        return self.results


class App(MyPlaybook):
    """
    this is a app object for inclue the common playbook.
    """
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)


if __name__ == "__main__":

#   resource =  {
#                "group1": {
#                    "hosts": [{"hostname": "127.0.0.1", "port": "22", "username": "root", "password": "xxx"},],
#                    "vars" : {"var1": "value1", "var2": "value2"},
#                          },
#                }

    resource = [{"hostname": "127.0.0.1", "port": "22", "username": "yumaojun", "password": "yusky0902",
                 # "ansible_become": "yes",
                 # "ansible_become_method": "sudo",
                 # # "ansible_become_user": "root",
                 # "ansible_become_pass": "yusky0902",
                 }]
    cmd.run('ls',pattern='*')
    print cmd.results_raw

    # resource = [{"hostname": "192.168.10.148", "port": "22", "username": "root", "password": "xxx"}]
    # task = Tasks(resource)
    # print task.get_host_info()

#   playbook = MyPlaybook(resource)
#   playbook.run('test.yml')
#   print playbook.raw_results

#    task = Tasks(resource)
    # print task.add_user('test', 'mypass')
#   print task.del_user('test')
#   print task.push_key('root', '/root/.ssh/id_rsa.pub')
#   print task.del_key('root', '/root/.ssh/id_rsa.pub')

#   task = Tasks(resource)
#   print task.add_init_users()
#   print task.del_init_users()


