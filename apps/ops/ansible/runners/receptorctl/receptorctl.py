from django.conf import settings
from receptorctl import ReceptorControl


class ReceptorCtl:
    @property
    def ctl(self):
        return ReceptorControl("tcp://{}".format(settings.ANSIBLE_RECEPTOR_TCP_LISTEN_ADDRESS))

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
