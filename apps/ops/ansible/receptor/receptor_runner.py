import concurrent.futures
import os
import queue
import socket

from django.conf import settings
import ansible_runner
from django.utils.functional import LazyObject
from receptorctl import ReceptorControl

from ops.ansible.cleaner import WorkPostRunCleaner, cleanup_post_run


class WarpedReceptorctl(LazyObject):
    def _setup(self):
        self._wrapped = self.get_receptorctl()

    @staticmethod
    def get_receptorctl():
        return ReceptorControl(settings.ANSIBLE_RECEPTOR_SOCK_PATH)


receptor_ctl = WarpedReceptorctl()


def cancel(unit_id):
    return receptor_ctl.simple_command("work cancel {}".format(unit_id))


def nodes():
    return receptor_ctl.simple_command("status").get("Advertisements", None)


def run(**kwargs):
    receptor_runner = AnsibleReceptorRunner(**kwargs)
    return receptor_runner.run()


class AnsibleReceptorRunner(WorkPostRunCleaner):
    def __init__(self, **kwargs):
        self.runner_params = kwargs
        self.unit_id = None

    def write_unit_id(self):
        if not self.unit_id:
            return
        private_dir = self.runner_params.get("private_data_dir", "")
        with open(os.path.join(private_dir, "local.unitid"), "w") as f:
            f.write(self.unit_id)
            f.flush()

    @property
    def clean_dir(self):
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
