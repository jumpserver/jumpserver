FROM python:3.8-slim
MAINTAINER JumpServer Team <ibuler@qq.com>

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
    unzip                               \
    wget"

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list \
    && apt update && sleep 1 && apt update \
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

ARG TARGETARCH
ARG ORACLE_LIB_MAJOR=19
ARG ORACLE_LIB_MINOR=10
ENV ORACLE_FILE="instantclient-basiclite-linux.${TARGETARCH:-amd64}-${ORACLE_LIB_MAJOR}.${ORACLE_LIB_MINOR}.0.0.0dbru.zip"

RUN mkdir -p /opt/oracle/ \
    && cd /opt/oracle/ \
    && wget https://download.jumpserver.org/files/oracle/${ORACLE_FILE} \
    && unzip instantclient-basiclite-linux.${TARGETARCH-amd64}-19.10.0.0.0dbru.zip \
    && mv instantclient_${ORACLE_LIB_MAJOR}_${ORACLE_LIB_MINOR} instantclient \
    && echo "/opt/oracle/instantclient" > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig \
    && rm -f ${ORACLE_FILE}

WORKDIR /tmp/build
COPY ./requirements ./requirements

ARG PIP_MIRROR=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_MIRROR=$PIP_MIRROR
ARG PIP_JMS_MIRROR=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_JMS_MIRROR=$PIP_JMS_MIRROR
# 因为以 jms 或者 jumpserver 开头的 mirror 上可能没有
RUN pip install --upgrade pip==20.2.4 setuptools==49.6.0 wheel==0.34.2 -i ${PIP_MIRROR} \
    && pip install --no-cache-dir $(grep -E 'jms|jumpserver' requirements/requirements.txt) -i ${PIP_JMS_MIRROR} \
    && pip install --no-cache-dir -r requirements/requirements.txt -i ${PIP_MIRROR} \
    && rm -rf ~/.cache/pip

ARG VERSION
ENV VERSION=$VERSION

ADD . .
RUN cd utils \
    && bash -ixeu build.sh \
    && mv ../release/jumpserver /opt/jumpserver \
    && rm -rf /tmp/build \
    && echo > /opt/jumpserver/config.yml

WORKDIR /opt/jumpserver
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8

EXPOSE 8070
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
