from private_storage.servers import NginxXAccelRedirectServer, DjangoServer


class StaticFileServer(object):

    @staticmethod
    def serve(private_file):
        full_path = private_file.full_path
        # todo: gzip 文件录像 nginx 处理后，浏览器无法正常解析内容
        # 造成在线播放失败，暂时仅使用 nginx 处理 mp4 录像文件
        if full_path.endswith('.mp4'):
            return NginxXAccelRedirectServer.serve(private_file)
        else:
            return DjangoServer.serve(private_file)
