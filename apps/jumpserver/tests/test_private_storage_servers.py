from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch, sentinel

from django.test import RequestFactory, SimpleTestCase, override_settings

from jumpserver.rewriting.storage.servers import StaticFileServer


class StaticFileServerTests(SimpleTestCase):
    @staticmethod
    def private_file(path):
        return SimpleNamespace(full_path=path)

    @override_settings(DEBUG_DEV=True)
    @patch('jumpserver.rewriting.storage.servers.NginxXAccelRedirectServer.serve')
    @patch('jumpserver.rewriting.storage.servers.DjangoServer.serve', return_value=sentinel.response)
    def test_dev_mp4_uses_django_file_response(self, django_serve, nginx_serve):
        private_file = self.private_file('/media/replay/session.part.mp4')

        self.assertIs(StaticFileServer.serve(private_file), sentinel.response)

        django_serve.assert_called_once_with(private_file)
        nginx_serve.assert_not_called()

    @override_settings(DEBUG_DEV=True)
    def test_dev_mp4_response_contains_file_bytes(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'session.part.mp4'
            path.write_bytes(b'test video bytes')
            private_file = SimpleNamespace(
                full_path=str(path),
                request=RequestFactory().get('/media/replay/session.part.mp4'),
            )

            response = StaticFileServer.serve(private_file)
            try:
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('X-Accel-Redirect', response)
                self.assertEqual(b''.join(response.streaming_content), b'test video bytes')
            finally:
                response.close()

    @override_settings(DEBUG_DEV=False, DEBUG=True)
    @patch('jumpserver.rewriting.storage.servers.NginxXAccelRedirectServer.serve', return_value=sentinel.response)
    @patch('jumpserver.rewriting.storage.servers.DjangoServer.serve')
    def test_non_dev_mp4_keeps_nginx_accel(self, django_serve, nginx_serve):
        private_file = self.private_file('/media/replay/session.part.mp4')

        self.assertIs(StaticFileServer.serve(private_file), sentinel.response)

        nginx_serve.assert_called_once_with(private_file)
        django_serve.assert_not_called()

    @override_settings(DEBUG_DEV=False)
    @patch('jumpserver.rewriting.storage.servers.NginxXAccelRedirectServer.serve')
    @patch('jumpserver.rewriting.storage.servers.DjangoServer.serve', return_value=sentinel.response)
    def test_other_files_keep_django_server(self, django_serve, nginx_serve):
        private_file = self.private_file('/media/replay/session.replay.json')

        self.assertIs(StaticFileServer.serve(private_file), sentinel.response)

        django_serve.assert_called_once_with(private_file)
        nginx_serve.assert_not_called()
