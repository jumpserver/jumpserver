"""ClickHouse's secondary backend endpoint, not a login protocol."""

CLICKHOUSE_HTTP_PROTOCOL = 'clickhouse_http'
CLICKHOUSE_HTTP_DEFAULT_PORT = 8123


def parse_clickhouse_http_port(value):
    value = str(value)
    if value.isascii() and value.isdecimal() and len(value) <= 5:
        port = int(value)
        if 1 <= port <= 65535:
            return port
    return None
