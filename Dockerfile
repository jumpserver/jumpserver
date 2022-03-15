# 编译代码
FROM python:3.8-slim as stage-build
MAINTAINER JumpServer Team <ibuler@qq.com>
ARG VERSION
ENV VERSION=$VERSION

WORKDIR /opt/jumpserver
ADD . .
RUN cd utils && bash -ixeu build.sh

FROM python:3.8-slim
ARG PIP_MIRROR=https://pypi.douban.com/simple
ENV PIP_MIRROR=$PIP_MIRROR
ARG PIP_JMS_MIRROR=https://pypi.douban.com/simple
ENV PIP_JMS_MIRROR=$PIP_JMS_MIRROR

WORKDIR /opt/jumpserver

ARG BUILD_DEPENDENCIES="              \
    g++                               \
    make                              \
    pkg-config"

ARG DEPENDENCIES="                    \
    default-libmysqlclient-dev        \
    freetds-dev                       \
    libpq-dev                         \
    libffi-dev                        \
    libldap2-dev                      \
    libsasl2-dev                      \
    libxml2-dev                       \
    libxmlsec1-dev                    \
    libxmlsec1-openssl                \
    libaio-dev                        \
    sshpass"

ARG TOOLS="                           \
    curl                              \
    default-mysql-client              \
    iproute2                          \
    iputils-ping                      \
    locales                           \
    procps                            \
    redis-tools                       \
    telnet                            \
    vim                               \
    wget"

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && apt update \
    && apt -y install ${BUILD_DEPENDENCIES} \
    && apt -y install ${DEPENDENCIES} \
    && apt -y install ${TOOLS} \
    && localedef -c -f UTF-8 -i zh_CN zh_CN.UTF-8 \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && mkdir -p /root/.ssh/ \
    && echo "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null" > /root/.ssh/config \
    && sed -i "s@# alias l@alias l@g" ~/.bashrc \
    && echo "set mouse-=a" > ~/.vimrc \
    && rm -rf /var/lib/apt/lists/* \
    && mv /bin/sh /bin/sh.bak  \
    && ln -s /bin/bash /bin/sh

RUN mkdir -p /opt/jumpserver/oracle/ \
    && wget https://download.jumpserver.org/public/instantclient-basiclite-linux.x64-21.1.0.0.0.tar \
    && tar xf instantclient-basiclite-linux.x64-21.1.0.0.0.tar -C /opt/jumpserver/oracle/ \
    && echo "/opt/jumpserver/oracle/instantclient_21_1" > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig \
    && rm -f instantclient-basiclite-linux.x64-21.1.0.0.0.tar

COPY --from=stage-build /opt/jumpserver/release/jumpserver /opt/jumpserver

RUN echo > config.yml \
    && pip install --upgrade pip==20.2.4 setuptools==49.6.0 wheel==0.34.2 -i ${PIP_MIRROR} \
    && pip install --no-cache-dir $(grep -E 'jms|jumpserver' requirements/requirements.txt) -i ${PIP_JMS_MIRROR} \
    && pip install --no-cache-dir -r requirements/requirements.txt -i ${PIP_MIRROR} \
    && rm -rf ~/.cache/pip

VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8

EXPOSE 8070
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
