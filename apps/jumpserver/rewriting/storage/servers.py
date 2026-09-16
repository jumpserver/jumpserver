from django.conf import settings
from private_storage.servers import NginxXAccelRedirectServer, DjangoServer


class StaticFileServer(object):

    @staticmethod
    def serve(private_file):
        full_path = private_file.full_path
        # Nginx handles MP4 in production; the dev server must stream it itself.
        # gzip replays keep using Django because Nginx changes their encoding.
        if full_path.endswith('.mp4') and not settings.DEBUG_DEV:
            return NginxXAccelRedirectServer.serve(private_file)
        else:
            return DjangoServer.serve(private_file)
