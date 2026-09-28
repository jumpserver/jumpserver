import json
import os

import psycopg2
from flask import Flask, Response


app = Flask(__name__)


@app.get('/')
def index():
    try:
        with open(os.environ['CREDENTIAL_FILE'], encoding='utf-8') as stream:
            credential = json.load(stream)

        connection = psycopg2.connect(
            host=os.getenv('PGHOST', 'host.docker.internal'),
            port=os.getenv('PGPORT', '5432'),
            dbname=os.getenv('PGDATABASE', 'orders_demo'),
            user=credential['username'],
            password=credential['secret'],
            connect_timeout=5,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT current_user, current_database(), '
                    "inet_server_addr()::text, inet_server_port(), "
                    "current_setting('server_version')"
                )
                user, database, host, port, version = cursor.fetchone()
        finally:
            connection.close()

        return Response(
            f'status: connected\n'
            f'server: {host}:{port}\n'
            f'database: {database}\n'
            f'user: {user}\n'
            f'postgresql_version: {version}\n'
            f'credential_key: {credential["key"]}\n'
            f'credential_revision: {credential["revision"]}\n',
            mimetype='text/plain',
        )
    except Exception as error:
        return Response(
            f'status: connection failed ({type(error).__name__})\n',
            status=503,
            mimetype='text/plain',
        )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
