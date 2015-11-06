# -*- coding: utf-8 -*-


from ansible.inventory.group   import Group
from ansible.inventory.host    import Host
from ansible.inventory         import Inventory
from ansible.runner            import Runner
from ansible.playbook          import PlayBook

from ansible                   import callbacks
from ansible                   import utils
from passlib.hash              import sha512_crypt

from utils                     import get_rand_pass


import os.path
API_DIR = os.path.dirname(os.path.abspath(__file__))
ANSIBLE_DIR = os.path.join(API_DIR, 'playbooks')



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


class MyInventory(object):
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
        self.inventory = Inventory()
        self.gen_inventory()

    def add_group(self, hosts, groupname, groupvars=None):
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
            hostname = host.pop("hostname")
            hostport = host.pop("port")
            username = host.pop("username")
            password = host.pop("password")
            my_host = Host(name=hostname, port=hostport)
            my_host.set_variable('ansible_ssh_host', hostname)
            my_host.set_variable('ansible_ssh_port', hostport)
            my_host.set_variable('ansible_ssh_user', username)
            my_host.set_variable('ansible_ssh_pass', password)
            # set other variables
            for key, value in host.iteritems():
                my_host.set_variable(key, value)
            # add to group
            my_group.add_host(my_host)

        self.inventory.add_group(my_group)

    def gen_inventory(self):
        """
        add hosts to inventory.
        """
        if isinstance(self.resource, list):
            self.add_group(self.resource, 'my_group')
        elif isinstance(self.resource, dict):
            for groupname, hosts_and_vars in self.resource.iteritems():
                self.add_group(hosts_and_vars.get("hosts"), groupname, hosts_and_vars.get("vars"))


class Command(MyInventory):
    """
    this is a command object for parallel execute command.
    """
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def run(self, command, module_name="command", timeout=5, forks=10):
        """
        run command from andible ad-hoc.
        command  : 必须是一个需要执行的命令字符串， 比如 
                 'uname -a'
        """
        if module_name not in ["raw", "command", "shell"]:
            raise  CommandValueError("module_name",
                                     "module_name must be of the 'raw, command, shell'")
        hoc = Runner(module_name=module_name,
                     module_args=command,
                     timeout=timeout,
                     inventory=self.inventory,
                     subset='my_group',
                     forks=forks
                     )

        self.results = hoc.run()
        return self.stdout

    @property
    def raw_results(self):
        """
        get the ansible raw results.
        """
        return self.results

    @property
    def exec_time(self):
        """
        get the command execute time.
        """
        result = {}
        all = self.results.get("contacted")
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
        all = self.results.get("contacted")
        for key, value in all.iteritems():
            result[key] =  value.get("stdout")
        return result

    @property
    def stderr(self):
        """
        get the command standard error.
        """
        result = {}
        all = self.results.get("contacted")
        for key, value in all.iteritems():
            result[key] = {
                    "stderr": value.get("stderr"),
                    "warnings": value.get("warnings"),}
        return result

    @property
    def dark(self):
        """
        get the dark results.
        """
        return self.results.get("dark")


class Tasks(Command):
    """
    this is a tasks object for include the common command.
    """
    def __init__(self, *args, **kwargs):
        super(Tasks, self).__init__(*args, **kwargs)

    def __run(self, module_args, module_name="command", timeout=5, forks=10):
        """
        run command from andible ad-hoc.
        command  : 必须是一个需要执行的命令字符串， 比如 
                 'uname -a'
        """
        hoc = Runner(module_name=module_name,
                     module_args=module_args,
                     timeout=timeout,
                     inventory=self.inventory,
                     subset='my_group',
                     forks=forks
                     )

        self.results = hoc.run()

    @property
    def msg(self):
        """
        get the contacted and dark msg
        """
        msg = {}
        for result in ["contacted", "dark"]:
            all = self.results.get(result)
            for key, value in all.iteritems():
                if value.get("msg"):
                    msg[key] = value.get("msg")
        return msg

    def push_key(self, user, key_path):
        """
        push the ssh authorized key to target.
        """
        module_args = 'user="%s" key="{{ lookup("file", "%s") }}"' % (user, key_path)
        self.__run(module_args, "authorized_key")

        return {"status": "failed","msg": self.msg} if self.msg else {"status": "ok"}

    def del_key(self, user, key_path):
        """
        push the ssh authorized key to target.
        """
        module_args = 'user="%s" key="{{ lookup("file", "%s") }}" state="absent"' % (user, key_path)
        self.__run(module_args, "authorized_key")

        return {"status": "failed","msg": self.msg} if self.msg else {"status": "ok"}

    def add_user(self, username, password):
        """
        add a host user.
        """
        encrypt_pass = sha512_crypt.encrypt(password)
        module_args = 'name=%s shell=/bin/bash password=%s' % (username, encrypt_pass)
        self.__run(module_args, "user")

        return {"status": "failed","msg": self.msg} if self.msg else {"status": "ok"}

    def del_user(self, username):
        """
        delete a host user.
        """
        module_args = 'name=%s state=absent remove=yes move_home=yes force=yes' % (username)
        self.__run(module_args, "user")

        return {"status": "failed","msg": self.msg} if self.msg else {"status": "ok"}

    def add_init_users(self):
        """
        add initail users: SA, DBA, DEV
        """
        results = {}
        action = results["action_info"] = {}
        users = {"SA": get_rand_pass(), "DBA": get_rand_pass(), "DEV": get_rand_pass()}
        for user, password in users.iteritems():
            ret = self.add_user(user, password)
            action[user] = ret
        results["user_info"] = users

        return results

    def del_init_users(self):
        """
        delete initail users: SA, DBA, DEV
        """
        results = {}
        action = results["action_info"] = {}
        for user in ["SA", "DBA", "DEV"]:
            ret = self.del_user(user)
            action[user] = ret
        return results



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
            playbook = playbook_path,
            stats = stats,
            callbacks = playbook_cb,
            runner_callbacks = runner_cb,
            inventory = self.inventory,
            extra_vars = extra_vars,
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
    pass
#   resource =  [{"hostname": "192.168.10.128", "port": "22", "username": "root", "password": "yusky0902"}]
#   playbook = MyPlaybook(resource)
#   playbook.run('test.yml')
#   print playbook.raw_results
#   command = Command(resource)
#   command.run("who")
#   print command.raw_results


#   task = Tasks(resource)
#   print task.add_user('test', 'mypass')
#   print task.del_user('test')
#   print task.push_key('root', '/root/.ssh/id_rsa.pub')
#   print task.del_key('root', '/root/.ssh/id_rsa.pub')


#   task = Tasks(resource)
#   print task.add_init_users()
#   print task.del_init_users()


