import concurrent.futures
import os
import queue
import socket

import ansible_runner

from ops.ansible.cleaner import cleanup_post_run
from ops.ansible.receptor.receptorctl import receptor_ctl
from ops.ansible.runners.base import BaseRunner


def run(**kwargs):
    _runner = AnsibleReceptorRunner(**kwargs)
    return _runner.run()


class AnsibleReceptorRunner(BaseRunner):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.unit_id = None
        self.stdout_queue = None

    def write_unit_id(self):
        if not self.unit_id:
            return
        private_dir = self.runner_params.get("private_data_dir", "")
        with open(os.path.join(private_dir, "local.unitid"), "w") as f:
            f.write(self.unit_id)
            f.flush()

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

        self.stdout_queue = queue.Queue()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            processor_future = executor.submit(self.processor, result_file)

            while not processor_future.done() or \
                    not self.stdout_queue.empty():
                msg = self.stdout_queue.get()
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

    def get_event_handler(self):
        _event_handler = super().get_event_handler()

        def _handler(data, **kwargs):
            stdout = data.get('stdout', '')
            if stdout:
                self.stdout_queue.put(stdout)
            _event_handler(data, **kwargs)

        return _handler

    def processor(self, _result_file):
        try:
            return ansible_runner.interface.run(
                quite=True,
                streamer='process',
                _input=_result_file,
                event_handler=self.get_event_handler(),
                status_handler=self.get_status_handler(),
                **self.runner_params,
            )
        finally:
            self.stdout_queue.put(None)
