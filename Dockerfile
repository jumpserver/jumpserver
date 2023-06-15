FROM python:3.9-slim-buster as stage-build
ARG TARGETARCH

ARG VERSION
ENV VERSION=$VERSION

WORKDIR /opt/jumpserver
ADD . .
RUN cd utils && bash -ixeu build.sh

FROM python:3.9-slim-buster
ARG TARGETARCH
MAINTAINER JumpServer Team <ibuler@qq.com>

ARG BUILD_DEPENDENCIES="              \
        g++                           \
        make                          \
        pkg-config"

ARG DEPENDENCIES="                    \
        freetds-dev                   \
        libpq-dev                     \
        libffi-dev                    \
        libjpeg-dev                   \
        libldap2-dev                  \
        libsasl2-dev                  \
        libxml2-dev                   \
        libxmlsec1-dev                \
        libxmlsec1-openssl            \
        freerdp2-dev                  \
        libaio-dev"

ARG TOOLS="                           \
        ca-certificates               \
        curl                          \
        default-libmysqlclient-dev    \
        default-mysql-client          \
        locales                       \
        openssh-client                \
        procps                        \
        sshpass                       \
        telnet                        \
        unzip                         \
        vim                           \
        git                           \
        wget"

ARG APT_MIRROR=http://mirrors.ustc.edu.cn

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked,id=core \
    sed -i "s@http://.*.debian.org@${APT_MIRROR}@g" /etc/apt/sources.list \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && apt-get update \
    && apt-get -y install --no-install-recommends ${BUILD_DEPENDENCIES} \
    && apt-get -y install --no-install-recommends ${DEPENDENCIES} \
    && apt-get -y install --no-install-recommends ${TOOLS} \
    && mkdir -p /root/.ssh/ \
    && echo "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null\n\tCiphers +aes128-cbc\n\tKexAlgorithms +diffie-hellman-group1-sha1\n\tHostKeyAlgorithms +ssh-rsa" > /root/.ssh/config \
    && echo "set mouse-=a" > ~/.vimrc \
    && echo "no" | dpkg-reconfigure dash \
    && echo "zh_CN.UTF-8" | dpkg-reconfigure locales \
    && sed -i "s@# export @export @g" ~/.bashrc \
    && sed -i "s@# alias @alias @g" ~/.bashrc \
    && rm -rf /var/lib/apt/lists/*

ARG DOWNLOAD_URL=https://download.jumpserver.org

RUN mkdir -p /opt/oracle/ \
    && cd /opt/oracle/ \
    && wget ${DOWNLOAD_URL}/public/instantclient-basiclite-linux.${TARGETARCH}-19.10.0.0.0.zip \
    && unzip instantclient-basiclite-linux.${TARGETARCH}-19.10.0.0.0.zip \
    && sh -c "echo /opt/oracle/instantclient_19_10 > /etc/ld.so.conf.d/oracle-instantclient.conf" \
    && ldconfig \
    && rm -f instantclient-basiclite-linux.${TARGETARCH}-19.10.0.0.0.zip

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
    && pip install $(grep -E 'jms|jumpserver' requirements/requirements.txt) -i ${PIP_JMS_MIRROR} \
    && pip install -r requirements/requirements.txt

COPY --from=stage-build /opt/jumpserver/release/jumpserver /opt/jumpserver
RUN echo > /opt/jumpserver/config.yml \
    && rm -rf /tmp/build

WORKDIR /opt/jumpserver
VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

ENV LANG=zh_CN.UTF-8

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
