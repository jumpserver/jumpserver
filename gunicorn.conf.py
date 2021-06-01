from apps.jumpserver.const import CONFIG

bind = '{}:{}'.format(
    CONFIG.HTTP_BIND_HOST or '127.0.0.1',
    CONFIG.HTTP_LISTEN_PORT or 8080
)

worker_class = 'gthread'

threads = 10
