# -*- coding: utf-8 -*-


from ansible.inventory.group   import Group
from ansible.inventory.host    import Host
from ansible.inventory         import Inventory
from ansible.runner            import Runner
from ansible.playbook          import PlayBook


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
        resource :
                 必须是一个字典列表，比如
                 [{"hostname": "10.10.10.10", "port": "22", 
                   "username": "test", "password": "mypass"}, ...] 
        """
        self.resource = resource
        self._gen_inventory()


    def _gen_inventory(self):
        """
        add hosts to inventory.
        """
        my_group = Group(name='my_group')

        for host in self.resource:
            hostname = host.get("hostname")
            hostport = host.get("hostport")
            username = host.get("username")
            password = host.get("password") 
            my_host = Host(name=hostname, port=hostport)
            my_host.set_variable('ansible_ssh_host', hostname)
            my_host.set_variable('ansible_ssh_port', hostport)
            my_host.set_variable('ansible_ssh_user', username) 
            my_host.set_variable('ansible_ssh_pass', password)
            my_group.add_host(my_host)

        my_inventory = Inventory()
        my_inventory.add_group(my_group)
        my_inventory.subset('my_group')

        self.inventory = my_inventory


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


class MyPlaybook(MyInventory):
    """
    this is my playbook object for execute playbook.
    """
    def __init__(self, *args, **kwargs):
        super(MyPlaybook, self).__init__(*args, **kwargs)


    def deploy(self):
        """
        use ansible playbook to deploy a application.
        """
        pass


class App(MyPlaybook):
    """
    this is a app object for inclue the common playbook.
    """
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)

        

if __name__ == "__main__":
   resource =  [{"hostname": "127.0.0.1",      "port": "22", "username": "root", "password": "xxx"},
                {"hostname": "192.168.10.128", "port": "22", "username": "root", "password": "xxx"}] 
   command = Command(resource)
   command.run("uname -a", "copy")
   print command.stdout
   print command.stderr
   print command.dark









