import concurrent.futures
import socket

import ansible_runner
from receptorctl import ReceptorControl

receptor_ctl = ReceptorControl('/tmp/control.sock')


def nodes():
    return receptor_ctl.simple_command("status").get("Advertisements", None)


def run(**kwargs):
    receptor_runner = AnsibleReceptorRunner(**kwargs)
    return receptor_runner.run()


class AnsibleReceptorRunner:
    def __init__(self, **kwargs):
        self.runner_params = kwargs
        self.unit_id = None

    def run(self):
        input, output = socket.socketpair()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            transmitter_future = executor.submit(self.transmit, input)
            result = receptor_ctl.submit_work(payload=output.makefile('rb'),
                                              node='primary', worktype='ansible-runner')
            input.close()
            output.close()

            self.unit_id = result['unitid']

        transmitter_future.result()

        result_file = receptor_ctl.get_work_results(self.unit_id, return_sockfile=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            processor_future = executor.submit(self.processor, result_file)
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

    def processor(self, _result_file):
        return ansible_runner.interface.run(
            streamer='process',
            _input=_result_file,
            **self.runner_params,
        )
