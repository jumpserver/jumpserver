FROM python:3.8-slim-bullseye as stage-build
ARG TARGETARCH

ARG VERSION
ENV VERSION=$VERSION

WORKDIR /opt/jumpserver
ADD . .
RUN cd utils && bash -ixeu build.sh

FROM python:3.8-slim-bullseye
ARG TARGETARCH
MAINTAINER JumpServer Team <ibuler@qq.com>

ARG BUILD_DEPENDENCIES="              \
        g++                           \
        make                          \
        pkg-config"

ARG DEPENDENCIES="                    \
        default-libmysqlclient-dev    \
        freetds-dev                   \
        libpq-dev                     \
        libffi-dev                    \
        libjpeg-dev                   \
        libldap2-dev                  \
        libsasl2-dev                  \
        libxml2-dev                   \
        libxmlsec1-dev                \
        libxmlsec1-openssl            \
        libaio-dev                    \
        openssh-client                \
        sshpass"

ARG TOOLS="                           \
        ca-certificates               \
        curl                          \
        default-mysql-client          \
        iputils-ping                  \
        locales                       \
        patch                         \
        procps                        \
        redis-tools                   \
        telnet                        \
        vim                           \
        unzip                         \
        wget"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked,id=core \
    sed -i 's@http://.*.debian.org@http://mirrors.ustc.edu.cn@g' /etc/apt/sources.list \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && apt-get update \
    && apt-get -y install --no-install-recommends ${BUILD_DEPENDENCIES} \
    && apt-get -y install --no-install-recommends ${DEPENDENCIES} \
    && apt-get -y install --no-install-recommends ${TOOLS} \
    && mkdir -p /root/.ssh/ \
    && echo "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null" > /root/.ssh/config \
    && sed -i "s@# alias l@alias l@g" ~/.bashrc \
    && echo "set mouse-=a" > ~/.vimrc \
    && echo "no" | dpkg-reconfigure dash \
    && echo "zh_CN.UTF-8" | dpkg-reconfigure locales \
    && rm -rf /var/lib/apt/lists/*

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

ARG PIP_MIRROR=https://pypi.douban.com/simple
ENV PIP_MIRROR=$PIP_MIRROR
ARG PIP_JMS_MIRROR=https://pypi.douban.com/simple
ENV PIP_JMS_MIRROR=$PIP_JMS_MIRROR

RUN --mount=type=cache,target=/root/.cache/pip \
    set -ex \
    && pip config set global.index-url ${PIP_MIRROR} \
    && pip install --upgrade pip \
    && pip install --upgrade setuptools wheel \
    && pip install Cython==0.29.35 \
    && pip install --no-build-isolation pymssql \
    && pip install $(grep -E 'jms|jumpserver' requirements/requirements.txt) -i ${PIP_JMS_MIRROR} \
    && pip install -r requirements/requirements.txt --use-deprecated=legacy-resolver

COPY --from=stage-build /opt/jumpserver/release/jumpserver /opt/jumpserver
RUN echo > /opt/jumpserver/config.yml \
    && rm -rf /tmp/build

WORKDIR /opt/jumpserver
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8

EXPOSE 8070
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
