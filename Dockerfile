FROM python:3.11-slim-bullseye as stage-1
ARG TARGETARCH

ARG DEPENDENCIES="                    \
        ca-certificates               \
        wget"

ARG APT_MIRROR=http://mirrors.ustc.edu.cn
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -ex \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' >/etc/apt/apt.conf.d/keep-cache \
    && sed -i "s@http://.*.debian.org@${APT_MIRROR}@g" /etc/apt/sources.list \
    && apt-get update \
    && apt-get -y install --no-install-recommends ${DEPENDENCIES} \
    && echo "no" | dpkg-reconfigure dash

WORKDIR /opt

ARG CHECK_VERSION=v1.0.2
RUN set -ex \
    && wget https://github.com/jumpserver-dev/healthcheck/releases/download/${CHECK_VERSION}/check-${CHECK_VERSION}-linux-${TARGETARCH}.tar.gz \
    && tar -xf check-${CHECK_VERSION}-linux-${TARGETARCH}.tar.gz \
    && mv check /usr/local/bin/ \
    && chown root:root /usr/local/bin/check \
    && chmod 755 /usr/local/bin/check \
    && rm -f check-${CHECK_VERSION}-linux-${TARGETARCH}.tar.gz

ARG RECEPTOR_VERSION=v1.4.5
RUN set -ex \
    && wget -O /opt/receptor.tar.gz https://github.com/ansible/receptor/releases/download/${RECEPTOR_VERSION}/receptor_${RECEPTOR_VERSION/v/}_linux_${TARGETARCH}.tar.gz \
    && tar -xf /opt/receptor.tar.gz -C /usr/local/bin/ \
    && chown root:root /usr/local/bin/receptor \
    && chmod 755 /usr/local/bin/receptor \
    && rm -f /opt/receptor.tar.gz

ARG VERSION
ENV VERSION=$VERSION

WORKDIR /opt/jumpserver
ADD . .
RUN echo > /opt/jumpserver/config.yml \
    && cd utils && bash -ixeu build.sh

FROM python:3.11-slim-bullseye as stage-2
ARG TARGETARCH

ARG BUILD_DEPENDENCIES="              \
        g++                           \
        make                          \
        pkg-config"

ARG DEPENDENCIES="                    \
        freetds-dev                   \
        libffi-dev                    \
        libjpeg-dev                   \
        libkrb5-dev                   \
        libldap2-dev                  \
        libpq-dev                     \
        libsasl2-dev                  \
        libssl-dev                    \
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
        git                           \
        git-lfs                       \
        unzip                         \
        xz-utils                      \
        wget"

ARG APT_MIRROR=http://mirrors.ustc.edu.cn
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -ex \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' >/etc/apt/apt.conf.d/keep-cache \
    && sed -i "s@http://.*.debian.org@${APT_MIRROR}@g" /etc/apt/sources.list \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && apt-get update \
    && apt-get -y install --no-install-recommends ${BUILD_DEPENDENCIES} \
    && apt-get -y install --no-install-recommends ${DEPENDENCIES} \
    && apt-get -y install --no-install-recommends ${TOOLS} \
    && echo "no" | dpkg-reconfigure dash

WORKDIR /opt/jumpserver

ARG PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=bind,source=poetry.lock,target=/opt/jumpserver/poetry.lock \
    --mount=type=bind,source=pyproject.toml,target=/opt/jumpserver/pyproject.toml \
    set -ex \
    && python3 -m venv /opt/py3 \
    && pip install poetry -i ${PIP_MIRROR} \
    && poetry config virtualenvs.create false \
    && . /opt/py3/bin/activate \
    && poetry install --only=main

FROM python:3.11-slim-bullseye
ARG TARGETARCH
ENV LANG=en_US.UTF-8 \
    PATH=/opt/py3/bin:$PATH

ARG DEPENDENCIES="                    \
        libldap2-dev                  \
        libpq-dev                     \
        libx11-dev                    \
        libxmlsec1-openssl"

ARG TOOLS="                           \
        ca-certificates               \
        default-libmysqlclient-dev    \
        openssh-client                \
        sshpass"

ARG APT_MIRROR=http://mirrors.ustc.edu.cn
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -ex \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' >/etc/apt/apt.conf.d/keep-cache \
    && sed -i "s@http://.*.debian.org@${APT_MIRROR}@g" /etc/apt/sources.list \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && apt-get update \
    && apt-get -y install --no-install-recommends ${DEPENDENCIES} \
    && apt-get -y install --no-install-recommends ${TOOLS} \
    && mkdir -p /root/.ssh/ \
    && echo "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null\n\tCiphers +aes128-cbc\n\tKexAlgorithms +diffie-hellman-group1-sha1\n\tHostKeyAlgorithms +ssh-rsa" > /root/.ssh/config \
    && echo "no" | dpkg-reconfigure dash \
    && sed -i "s@# export @export @g" ~/.bashrc \
    && sed -i "s@# alias @alias @g" ~/.bashrc

COPY --from=stage-2 /opt/py3 /opt/py3
COPY --from=stage-1 /usr/local/bin /usr/local/bin
COPY --from=stage-1 /opt/jumpserver/release/jumpserver /opt/jumpserver
COPY --from=stage-1 /opt/jumpserver/release/jumpserver/apps/libs/ansible/ansible.cfg /etc/ansible/

WORKDIR /opt/jumpserver

ARG VERSION
ENV VERSION=$VERSION

VOLUME /opt/jumpserver/data

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
