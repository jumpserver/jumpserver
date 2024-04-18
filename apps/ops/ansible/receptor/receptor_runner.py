import concurrent.futures
import os
import queue
import socket

from django.conf import settings
import ansible_runner
from receptorctl import ReceptorControl

from ops.ansible.cleaner import WorkPostRunCleaner, cleanup_post_run


class ReceptorCtl:
    @property
    def ctl(self):
        return ReceptorControl(settings.ANSIBLE_RECEPTOR_SOCK_PATH)

    def cancel(self, unit_id):
        return self.ctl.simple_command("work cancel {}".format(unit_id))

    def nodes(self):
        return self.ctl.simple_command("status").get("Advertisements", None)

    def submit_work(self,
                    worktype,
                    payload,
                    node=None,
                    tlsclient=None,
                    ttl=None,
                    signwork=False,
                    params=None, ):
        return self.ctl.submit_work(worktype, payload, node, tlsclient, ttl, signwork, params)

    def get_work_results(self, unit_id, startpos=0, return_socket=False, return_sockfile=True):
        return self.ctl.get_work_results(unit_id, startpos, return_socket, return_sockfile)

    def kill_process(self, pid):
        submit_result = self.submit_work(worktype="kill", node="primary", payload=str(pid))
        unit_id = submit_result["unitid"]
        result_socket, result_file = self.get_work_results(unit_id=unit_id, return_sockfile=True,
                                                           return_socket=True)
        while not result_socket.close():
            buf = result_file.read()
            if not buf:
                break
            print(buf.decode('utf8'))


receptor_ctl = ReceptorCtl()


def run(**kwargs):
    receptor_runner = AnsibleReceptorRunner(**kwargs)
    return receptor_runner.run()


class AnsibleReceptorRunner(WorkPostRunCleaner):
    def __init__(self, **kwargs):
        self.runner_params = kwargs
        self.unit_id = None
        self.clean_workspace = kwargs.pop("clean_workspace", True)

    def write_unit_id(self):
        if not self.unit_id:
            return
        private_dir = self.runner_params.get("private_data_dir", "")
        with open(os.path.join(private_dir, "local.unitid"), "w") as f:
            f.write(self.unit_id)
            f.flush()

    @property
    def clean_dir(self):
        if not self.clean_workspace:
            return None
        return self.runner_params.get("private_data_dir", None)

    @cleanup_post_run
    def run(self):
        input, output = socket.socketpair()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            transmitter_future = executor.submit(self.transmit, input)
            result = receptor_ctl.submit_work(payload=output.makefile('rb'),
                                              node='primary', worktype='ansible-runner')
            input.close()
            output.close()

            self.unit_id = result['unitid']
            self.write_unit_id()

        transmitter_future.result()

        result_file = receptor_ctl.get_work_results(self.unit_id, return_sockfile=True)

        stdout_queue = queue.Queue()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            processor_future = executor.submit(self.processor, result_file, stdout_queue)

            while not processor_future.done() or \
                    not stdout_queue.empty():
                msg = stdout_queue.get()
                if msg is None:
                    break
                print(msg)

        return processor_future.result()

    def transmit(self, _socket):
        try:
            ansible_runner.run(
                streamer='transmit',
                _output=_socket.makefile('wb'),
                **self.runner_params
            )
        finally:
            _socket.shutdown(socket.SHUT_WR)

    def processor(self, _result_file, stdout_queue):
        try:
            original_event_handler = self.runner_params.pop("event_handler", None)
            original_status_handler = self.runner_params.pop("status_handler", None)

            def event_handler(data, **kwargs):
                stdout = data.get('stdout', '')
                if stdout:
                    stdout_queue.put(stdout)
                if original_event_handler:
                    original_event_handler(data, **kwargs)

            def status_handler(data, **kwargs):
                private_data_dir = self.runner_params.get("private_data_dir", None)
                if private_data_dir:
                    data["private_data_dir"] = private_data_dir
                if original_status_handler:
                    original_status_handler(data, **kwargs)

            return ansible_runner.interface.run(
                quite=True,
                streamer='process',
                _input=_result_file,
                event_handler=event_handler,
                status_handler=status_handler,
                **self.runner_params,
            )
        finally:
            stdout_queue.put(None)
