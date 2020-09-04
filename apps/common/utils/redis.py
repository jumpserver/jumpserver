import redis


class RedisClient(object):
    def __init__(self, host, port=6379, password='', db='0'):
        self.conn = redis.Redis(host=host, port=port, password=password, db=db, decode_responses=True)

    def delete(self, *names):
        self.conn.delete(*names)



