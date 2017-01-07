FROM jumpserver/base-env-alpine:latest
MAINTAINER Jumpserver Team <ibuler@qq.com>

#RUN apk add --update python gcc python-dev py-pip musl-dev linux-headers \
#        libffi-dev openssl-dev jpeg-dev redis  && rm -rf /var/cache/apk/*
COPY . /opt/jumpserver
WORKDIR /opt/jumpserver

#RUN pip install -r requirements.txt -i https://pypi.doubanio.com/simple
RUN rm -f db.sqlite3 && cd utils && sh make_migrations.sh && sh init_db.sh
EXPOSE 8080
CMD redis-server utils/redis.conf && python run_server.py