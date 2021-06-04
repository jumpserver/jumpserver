from jumpserver.const import CONFIG

bind = '{}:{}'.format(
    CONFIG.HTTP_BIND_HOST or '127.0.0.1',
    CONFIG.HTTP_LISTEN_PORT or 8080
)

worker_class = 'gthread'

threads = 10

# https://docs.gunicorn.org/en/latest/settings.html#workers
workers = 4

# https://docs.gunicorn.org/en/latest/settings.html#max-requests
max_requests = 4096

# https://docs.gunicorn.org/en/latest/settings.html#access-log-format
access_log_format = '%(h)s %(t)s %(L)ss "%(r)s" %(s)s %(b)s '

# https://docs.gunicorn.org/en/latest/settings.html#accesslog
accesslog = '-'

# https://docs.gunicorn.org/en/latest/settings.html#reload
reload = CONFIG.DEBUG
