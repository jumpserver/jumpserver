import os
import queue
import socket
import threading
import time

import paramiko
import sshtunnel
from sshtunnel import SSHTunnelForwarder


class GatewayConnectTimeout(TimeoutError):
    pass


class TimeoutSSHTunnelForwarder(SSHTunnelForwarder):
    """SSHTunnelForwarder with a bounded gateway start phase."""

    def __init__(self, *args, **kwargs):
        connect_timeout = kwargs.pop('connect_timeout', None)
        if connect_timeout is None:
            connect_timeout = os.getenv(
                'JMS_SSH_GATEWAY_CONNECT_TIMEOUT', 30
            )
        self.connect_timeout = float(connect_timeout or 0)
        self._connect_deadline = None
        self._connect_timed_out = threading.Event()
        self._connecting_socket = None
        self._connect_state_lock = threading.Lock()
        self._connect_finished = True
        super().__init__(*args, **kwargs)

    def _remaining_connect_time(self):
        if not self._connect_deadline:
            return self.connect_timeout
        remaining = self._connect_deadline - time.monotonic()
        if remaining <= 0 or self._connect_timed_out.is_set():
            self._connect_timed_out.set()
            raise GatewayConnectTimeout(
                'SSH gateway connection timed out after {} seconds'.format(
                    self.connect_timeout
                )
            )
        return remaining

    def _connect_gateway_socket(self):
        addresses = self._resolve_gateway_addresses()
        last_error = None
        for family, socktype, proto, _, address in addresses:
            gateway_socket = socket.socket(family, socktype, proto)
            self._connecting_socket = gateway_socket
            try:
                gateway_socket.settimeout(self._remaining_connect_time())
                gateway_socket.connect(address)
                return gateway_socket
            except OSError as error:
                last_error = error
                gateway_socket.close()
                self._remaining_connect_time()

        if last_error:
            raise last_error
        raise OSError(
            'Unable to resolve SSH gateway {}:{}'.format(
                self.ssh_host, self.ssh_port
            )
        )

    def _resolve_gateway_addresses(self):
        getaddrinfo_args = (
            self.ssh_host,
            self.ssh_port,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )
        try:
            return socket.getaddrinfo(
                *getaddrinfo_args, flags=socket.AI_NUMERICHOST
            )
        except socket.gaierror:
            pass

        result_queue = queue.Queue(maxsize=1)

        def resolve():
            try:
                result_queue.put((socket.getaddrinfo(*getaddrinfo_args), None))
            except Exception as error:
                result_queue.put((None, error))

        resolver = threading.Thread(
            target=resolve,
            name='SSHGatewayResolver-{}'.format(self.ssh_host),
            daemon=True,
        )
        resolver.start()
        try:
            addresses, error = result_queue.get(
                timeout=self._remaining_connect_time()
            )
        except queue.Empty as error:
            self._connect_timed_out.set()
            raise GatewayConnectTimeout(
                'SSH gateway DNS resolution timed out after {} seconds'.format(
                    self.connect_timeout
                )
            ) from error
        if error:
            raise error
        return addresses

    def _configure_transport_timeouts(self, transport):
        remaining = self._remaining_connect_time()
        transport.banner_timeout = remaining
        transport.handshake_timeout = remaining
        transport.auth_timeout = remaining
        transport.channel_timeout = remaining
        transport.set_keepalive(self.set_keepalive)
        transport.use_compression(compress=self.compression)
        transport.daemon = self.daemon_transport
        if isinstance(transport.sock, socket.socket):
            transport.sock.settimeout(
                min(sshtunnel.SSH_TIMEOUT, remaining)
            )
        return transport

    def _get_transport(self):
        if self.connect_timeout <= 0:
            return super()._get_transport()
        if self.ssh_proxy:
            transport = super()._get_transport()
        else:
            gateway_socket = self._connect_gateway_socket()
            transport = paramiko.Transport(gateway_socket)
        return self._configure_transport_timeouts(transport)

    def _abort_connect(self):
        with self._connect_state_lock:
            if self._connect_finished:
                return
            self._connect_timed_out.set()

        connecting_socket = self._connecting_socket
        if connecting_socket:
            try:
                connecting_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                connecting_socket.close()
            except OSError:
                pass

        transport = getattr(self, '_transport', None)
        if transport:
            try:
                transport.close()
            except Exception:
                pass

        # Wake sshtunnel._check_tunnel immediately if it is waiting for the
        # forwarding handler to report whether the remote channel opened.
        for server in list(getattr(self, '_server_list', [])):
            try:
                server.tunnel_ok.put_nowait(False)
            except Exception:
                pass

    def _cleanup_failed_tunnel(self):
        try:
            self.stop(force=True)
        except Exception:
            pass

        transport = getattr(self, '_transport', None)
        if transport:
            try:
                transport.close()
            except Exception:
                pass
        for server in list(getattr(self, '_server_list', [])):
            try:
                server.shutdown()
            except Exception:
                pass
            try:
                server.server_close()
            except Exception:
                pass
        self._server_list = []
        self.tunnel_is_up = {}
        self.is_alive = False

    def _finish_connect_timer(self, timer):
        timer.cancel()
        with self._connect_state_lock:
            self._connect_finished = True
        self._connect_deadline = None
        self._connecting_socket = None

    def start(self):
        if self.connect_timeout <= 0:
            return super().start()

        self._connect_timed_out.clear()
        self._connect_deadline = time.monotonic() + self.connect_timeout
        with self._connect_state_lock:
            self._connect_finished = False
        timer = threading.Timer(self.connect_timeout, self._abort_connect)
        timer.daemon = True
        timer.start()
        try:
            try:
                result = super().start()
            finally:
                self._finish_connect_timer(timer)
        except Exception as error:
            self._cleanup_failed_tunnel()
            if self._connect_timed_out.is_set():
                raise GatewayConnectTimeout(
                    'SSH gateway connection timed out after {} seconds'.format(
                        self.connect_timeout
                    )
                ) from error
            raise

        if self._connect_timed_out.is_set():
            self._cleanup_failed_tunnel()
            raise GatewayConnectTimeout(
                'SSH gateway connection timed out after {} seconds'.format(
                    self.connect_timeout
                )
            )
        return result
