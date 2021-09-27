FROM python:3.8.6-slim as stage-build
MAINTAINER JumpServer Team <ibuler@qq.com>
ARG VERSION
ENV VERSION=$VERSION

WORKDIR /opt/jumpserver
ADD . .
RUN cd utils && bash -ixeu build.sh

FROM python:3.8.6-slim
ARG PIP_MIRROR=https://pypi.douban.com/simple
ENV PIP_MIRROR=$PIP_MIRROR

WORKDIR /opt/jumpserver

COPY ./requirements/deb_requirements.txt ./requirements/deb_requirements.txt
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && apt update \
    && apt -y install telnet iproute2 redis-tools default-mysql-client vim wget curl locales procps \
    && apt -y install $(cat requirements/deb_requirements.txt) \
    && rm -rf /var/lib/apt/lists/* \
    && localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8 \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && sed -i "s@# alias l@alias l@g" ~/.bashrc \
    && echo "set mouse-=a" > ~/.vimrc

COPY ./requirements/requirements.txt ./requirements/requirements.txt
RUN pip install --upgrade pip==20.2.4 setuptools==49.6.0 wheel==0.34.2 -i ${PIP_MIRROR} \
    && pip install --no-cache-dir -r requirements/requirements.txt -i ${PIP_MIRROR} \
    && rm -rf ~/.cache/pip

COPY --from=stage-build /opt/jumpserver/release/jumpserver /opt/jumpserver
RUN mkdir -p /root/.ssh/ \
    && echo "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null" > /root/.ssh/config

RUN mkdir -p /opt/jumpserver/oracle/ \
    && wget https://download.jumpserver.org/public/instantclient-basiclite-linux.x64-21.1.0.0.0.tar > /dev/null \
    && tar xf instantclient-basiclite-linux.x64-21.1.0.0.0.tar -C /opt/jumpserver/oracle/ \
    && echo "/opt/jumpserver/oracle/instantclient_21_1" > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig \
    && rm -f instantclient-basiclite-linux.x64-21.1.0.0.0.tar

RUN cd apps && python manage.py compilemessages

RUN echo > config.yml
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8

EXPOSE 8070
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
