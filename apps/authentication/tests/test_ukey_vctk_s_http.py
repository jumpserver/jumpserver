"""VCTK_S wire protocol and transport failures, without a live service."""
import base64
import json
import socket
import ssl
import unittest
from http.client import BadStatusLine
from unittest.mock import MagicMock, patch

from authentication.backends.ukey.clients.fisherman import MAX_RESPONSE, SVSError
from authentication.backends.ukey.clients.vctk_s import MAX_P7_SIZE, VCTKSClient


CLIENT_MODULE = 'authentication.backends.ukey.clients.vctk_s'
TRANSPORT_MODULE = 'authentication.backends.ukey.clients.fisherman'
URL = 'http://192.168.10.5:8000'
CHALLENGE = '0123456789abcdef' * 4
SIGNATURE = base64.b64encode(b'P7 proof bytes\xfb\xff').decode('ascii')


def http_response(data=None):
    if data is None:
        data = json.dumps({'code': '0', 'message': '', 'data': {
            'plain': base64.b64encode(CHALLENGE.encode()).decode(),
            'certinfo': {'dscert': base64.b64encode(b'certificate').decode()},
            'digestalg': 'SHA256',
        }}).encode()
    response = MagicMock()
    response.__enter__.return_value = response
    response.status, response.length = 200, 0
    response.getheader.return_value = 'identity'
    response.read.return_value = data
    return response


class VCTKSProtocolTests(unittest.TestCase):
    def test_exact_success_codes_and_invalid_envelopes(self):
        for code in (0, '0'):
            self.assertEqual(VCTKSClient._decode_response(json.dumps({
                'code': code, 'message': '', 'data': {'version': 'v1'},
            }).encode()), {'version': 'v1'})
        for code in (False, True, None, 0.0, '00', ' 0', '+0', '', 1):
            with self.subTest(code=code), self.assertRaises(SVSError):
                VCTKSClient._decode_response(json.dumps({
                    'code': code, 'message': 'sensitive error', 'data': {},
                }).encode())
        for data in (b'{}', b'[]', b'null', b'{"code":0}', b'\xff',
                     b'{"code":1,"code":0,"message":"","data":{}}',
                     b'{"code":0,"message":"","data":null}',
                     b'{"code":0,"message":"","data":{"plain":"a","plain":"b"}}'):
            with self.subTest(data=data), self.assertRaises(SVSError):
                VCTKSClient._decode_response(data)

    def test_random_generation_and_optional_authorization_headers(self):
        for username, password in (('', ''), ('business', 'secret'), ('', 'saved-secret')):
            client = VCTKSClient(URL, username=username, password=password)
            connection = MagicMock()
            random = bytes(range(32))
            connection.getresponse.return_value = http_response(json.dumps({
                'code': 0, 'message': '', 'data': {
                    'randomResult': base64.b64encode(random).decode(),
                },
            }).encode())
            with patch.object(client, '_connect', return_value=connection):
                self.assertEqual(client.generate_random(), random)
            args, kwargs = connection.request.call_args
            self.assertEqual(args, ('POST', '/api/v1/generateRandom'))
            self.assertEqual(json.loads(kwargs['body']), {'randomlength': '32'})
            headers = kwargs['headers']
            self.assertEqual(headers['messagetype'], 'json')
            self.assertRegex(headers['serialnumber'], r'^[0-9a-f]{32}$')
            self.assertEqual(headers['Content-Type'], 'application/json;charset=UTF-8')
            self.assertNotIn('token', headers)
            if username:
                self.assertEqual((headers['une'], headers['pwd']), (username, password))
            else:
                self.assertNotIn('une', headers)
                self.assertNotIn('pwd', headers)
            connection.close.assert_called_once()

    def test_random_length_and_encoding_fail_closed(self):
        client = VCTKSClient(URL)
        invalid = [None, [], '!', '', base64.b64encode(b'x' * 31).decode(),
                   base64.b64encode(b'x' * 33).decode(), 'mVvRR+O7eAAc']
        for value in invalid:
            with self.subTest(value=value), patch.object(
                client, '_request', return_value={'randomResult': value},
            ), self.assertRaises(SVSError):
                client.generate_random()

    def test_attached_verification_wire_and_result(self):
        client = VCTKSClient(URL)
        connection = MagicMock()
        connection.getresponse.return_value = http_response()
        with patch.object(client, '_connect', return_value=connection):
            result = client.verify_signed_data(SIGNATURE, 'sha256')
        self.assertEqual(result, {'plain': CHALLENGE.encode(), 'certificate': b'certificate'})
        connection.request.assert_called_once()
        args, kwargs = connection.request.call_args
        self.assertEqual(args, ('POST', '/api/v1/attachverifysign'))
        self.assertEqual(json.loads(kwargs['body']), {'signdata': SIGNATURE, 'digestalg': 'sha256'})
        connection.close.assert_called_once()

    def test_invalid_returned_plain_certificate_or_digest_is_rejected(self):
        client = VCTKSClient(URL)
        valid = {'plain': base64.b64encode(CHALLENGE.encode()).decode(),
                 'certinfo': {'dscert': base64.b64encode(b'cert').decode()}, 'digestalg': 'sha256'}
        for changed in ({'plain': None}, {'plain': '!'}, {'certinfo': {}},
                        {'certinfo': None}, {'digestalg': 'sha1'}, {'digestalg': None}):
            with self.subTest(changed=changed), patch.object(
                client, '_request', return_value={**valid, **changed},
            ), self.assertRaises(SVSError):
                client.verify_signed_data(SIGNATURE, 'sha256')

    def test_invalid_inputs_never_connect(self):
        client = VCTKSClient(URL)
        for signature, digest in (('', 'sha256'), (SIGNATURE, 'sha1'), (None, 'sm3'),
                                  (SIGNATURE + '\n', 'sm3'),
                                  (base64.b64encode(b'x' * (MAX_P7_SIZE + 1)).decode(), 'sm3')):
            with patch.object(client, '_connect') as connect, self.assertRaises(SVSError):
                client.verify_signed_data(signature, digest)
            connect.assert_not_called()
        for username, password in (('user', ''), ('user\r\nHeader: bad', 'pass'),
                                   ('user', 'pass\n'), ('user', 'a' * 257)):
            with self.assertRaises(SVSError):
                VCTKSClient(URL, username=username, password=password)

    def test_unsupported_operation_and_oversized_request_never_connect(self):
        client = VCTKSClient(URL)
        for operation, params in (
            ('JITGetVersion', {}), ('RegisterParam', {}), ('generateRandom', {}),
            ('attachverifysign', {'signdata': 'a' * MAX_RESPONSE, 'digestalg': 'sm3'}),
        ):
            with patch.object(client, '_connect') as connect, self.assertRaises(SVSError):
                client._request(operation, params)
            connect.assert_not_called()


class VCTKSTransportTests(unittest.TestCase):
    def test_url_tls_and_timeout_guards(self):
        for url in (
            'http://127.0.0.1', 'http://169.254.169.254', 'https://user:pw@example.com',
            URL + '/api', URL + '?x=1', URL + '#x',
        ):
            with self.subTest(url=url), self.assertRaises(SVSError):
                VCTKSClient(url)
        for kwargs in (
            {'connect_timeout': 0}, {'connect_timeout': 11}, {'read_timeout': 21},
            {'read_timeout': True}, {'tls_verify': 'custom'}, {'tls_verify': 'unknown'},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(SVSError):
                VCTKSClient('https://vctks.example.com', **kwargs)

    def test_https_verification_is_scoped_to_the_client(self):
        verified = VCTKSClient('https://vctks.example.com')
        insecure = VCTKSClient('https://vctks.example.com', tls_verify='insecure')
        self.assertEqual(verified.tls_context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(verified.tls_context.check_hostname)
        self.assertEqual(insecure.tls_context.verify_mode, ssl.CERT_NONE)
        self.assertFalse(insecure.tls_context.check_hostname)
        self.assertIsNone(VCTKSClient(URL).tls_context)
        with patch(CLIENT_MODULE + '.create_tls_context') as create_context:
            custom = VCTKSClient(
                'https://vctks.example.com', tls_verify='custom', tls_ca_cert='CA PEM',
            )
        create_context.assert_called_once_with('https', 'custom', 'CA PEM')
        self.assertIs(custom.tls_context, create_context.return_value)

    def test_http_failures_are_closed_without_retries(self):
        for kind in ('redirect', 'compressed', 'oversized', 'incomplete', 'timeout', 'invalid_headers'):
            client = VCTKSClient(URL)
            connection, response = MagicMock(), http_response()
            connection.getresponse.return_value = response
            if kind == 'redirect':
                response.status = 302
            elif kind == 'compressed':
                response.getheader.return_value = 'gzip'
            elif kind == 'oversized':
                response.read.return_value = b' ' * (MAX_RESPONSE + 1)
            elif kind == 'incomplete':
                response.length = 10
            elif kind == 'invalid_headers':
                connection.getresponse.side_effect = BadStatusLine('sensitive input')
            else:
                response.read.side_effect = TimeoutError('sensitive input')
            with self.subTest(kind=kind), patch.object(
                client, '_connect', return_value=connection,
            ) as connect, self.assertRaises(SVSError) as error:
                client.verify_signed_data(SIGNATURE, 'sha256')
            connect.assert_called_once()
            connection.request.assert_called_once()
            connection.close.assert_called_once()
            self.assertNotIn('sensitive input', str(error.exception))

    def test_read_deadline_aborts_the_socket_and_cancels_timer(self):
        client = VCTKSClient(URL, read_timeout=5)
        connection = MagicMock()
        connection.getresponse.return_value = http_response()
        with patch.object(client, '_connect', return_value=connection), patch(
            CLIENT_MODULE + '.threading.Timer',
        ) as timer, patch(CLIENT_MODULE + '.time.monotonic', side_effect=[10, 16]):
            with self.assertRaises(SVSError):
                client.verify_signed_data(SIGNATURE, 'sha256')
        timer.assert_called_once_with(5, client._abort_response, args=(connection.sock,))
        timer.return_value.start.assert_called_once()
        timer.return_value.cancel.assert_called_once()
        connection.close.assert_called_once()

    def test_transport_error_does_not_expose_exception_text(self):
        client = VCTKSClient(URL)
        with patch.object(client, '_connect', side_effect=OSError('sensitive input')):
            with self.assertRaises(SVSError) as error:
                client.verify_signed_data(SIGNATURE, 'sha256')
        self.assertNotIn('sensitive input', str(error.exception))

    def test_cleanup_error_does_not_expose_exception_text(self):
        client = VCTKSClient(URL)
        connection = MagicMock()
        connection.getresponse.return_value = http_response()
        connection.close.side_effect = OSError('sensitive input')
        with patch.object(client, '_connect', return_value=connection):
            with self.assertRaises(SVSError) as error:
                client.verify_signed_data(SIGNATURE, 'sha256')
        self.assertNotIn('sensitive input', str(error.exception))

    def test_https_connects_only_to_resolved_ip_and_keeps_hostname_for_tls(self):
        client = VCTKSClient('https://vctks.example.com:8000')
        client.tls_context = MagicMock()
        with patch.object(client, '_resolve_hosts', return_value=['192.168.10.5']) as resolve, patch(
            TRANSPORT_MODULE + '.socket.socket',
        ) as socket_factory, patch(TRANSPORT_MODULE + '.time.monotonic', return_value=10):
            connection = client._connect()
        resolve.assert_called_once_with(13)
        socket_factory.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        sock = socket_factory.return_value
        sock.connect.assert_called_once_with(('192.168.10.5', 8000))
        client.tls_context.wrap_socket.assert_called_once_with(sock, server_hostname='vctks.example.com')
        self.assertIs(connection.sock, client.tls_context.wrap_socket.return_value)
        self.assertEqual(connection.auto_open, 0)
        connection.close()

    def test_tls_failure_closes_socket_and_never_creates_a_connection(self):
        client = VCTKSClient('https://vctks.example.com')
        client.tls_context = MagicMock()
        client.tls_context.wrap_socket.side_effect = ssl.SSLCertVerificationError('sensitive input')
        with patch.object(client, '_resolve_hosts', return_value=['192.168.10.5']), patch(
            TRANSPORT_MODULE + '.socket.socket',
        ) as socket_factory, patch(TRANSPORT_MODULE + '.HTTPSConnection') as connection, patch(
            TRANSPORT_MODULE + '.time.monotonic', return_value=10,
        ):
            with self.assertRaises(SVSError) as error:
                client._connect()
        socket_factory.return_value.close.assert_called_once()
        connection.assert_not_called()
        self.assertNotIn('sensitive input', str(error.exception))

    def test_resolution_failure_never_opens_a_socket(self):
        client = VCTKSClient('http://vctks.example.com')
        with patch.object(client, '_resolve_hosts', side_effect=TimeoutError), patch(
            TRANSPORT_MODULE + '.socket.socket',
        ) as socket_factory:
            with self.assertRaises(SVSError):
                client.verify_signed_data(SIGNATURE, 'sha256')
        socket_factory.assert_not_called()

    def test_all_resolved_addresses_are_validated_before_connecting(self):
        client = VCTKSClient('http://vctks.example.com')
        records = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.10.5', 8000)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('169.254.169.254', 8000)),
        ]
        with patch(TRANSPORT_MODULE + '.socket.getaddrinfo', return_value=records), patch(
            TRANSPORT_MODULE + '.socket.socket',
        ) as socket_factory:
            with self.assertRaises(SVSError):
                client.verify_signed_data(SIGNATURE, 'sha256')
        socket_factory.assert_not_called()
