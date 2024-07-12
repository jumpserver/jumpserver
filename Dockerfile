FROM debian:bullseye-slim AS stage-1
ARG TARGETARCH

ARG DEPENDENCIES="                    \
        ca-certificates               \
        wget"

ARG APT_MIRROR=http://mirrors.ustc.edu.cn
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked,id=core \
    --mount=type=cache,target=/var/lib/apt,sharing=locked,id=core \
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

ARG VERSION

WORKDIR /opt/jumpserver
ADD . .
RUN echo > /opt/jumpserver/config.yml \
    && \
    if [ -n "${VERSION}" ]; then \
        sed -i "s@VERSION = .*@VERSION = '${VERSION}'@g" apps/jumpserver/const.py; \
    fi

FROM python:3.11-slim-bullseye AS stage-2
ARG TARGETARCH

ARG BUILD_DEPENDENCIES="              \
        g++                           \
        make                          \
        pkg-config"

ARG DEPENDENCIES="                    \
        default-libmysqlclient-dev    \
        freetds-dev                   \
        gettext                       \
        libkrb5-dev                   \
        libldap2-dev                  \
        libsasl2-dev"

ARG APT_MIRROR=http://mirrors.ustc.edu.cn
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked,id=core \
    --mount=type=cache,target=/var/lib/apt,sharing=locked,id=core \
    set -ex \
    && rm -f /etc/apt/apt.conf.d/docker-clean \
    && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' >/etc/apt/apt.conf.d/keep-cache \
    && sed -i "s@http://.*.debian.org@${APT_MIRROR}@g" /etc/apt/sources.list \
    && apt-get update \
    && apt-get -y install --no-install-recommends ${BUILD_DEPENDENCIES} \
    && apt-get -y install --no-install-recommends ${DEPENDENCIES} \
    && echo "no" | dpkg-reconfigure dash

WORKDIR /opt/jumpserver

ARG PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple
RUN --mount=type=cache,target=/root/.cache,sharing=locked,id=core \
    --mount=type=bind,source=poetry.lock,target=poetry.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    set -ex \
    && python3 -m venv /opt/py3 \
    && pip install poetry -i ${PIP_MIRROR} \
    && poetry config virtualenvs.create false \
    && . /opt/py3/bin/activate \
    && poetry install --only main

COPY --from=stage-1 /opt/jumpserver /opt/jumpserver

RUN set -ex \
    && export SECRET_KEY=$(head -c100 < /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c 48) \
    && . /opt/py3/bin/activate \
    && cd apps \
    && python manage.py compilemessages

FROM python:3.11-slim-bullseye
ARG TARGETARCH
ENV LANG=en_US.UTF-8 \
    PATH=/opt/py3/bin:$PATH

ARG DEPENDENCIES="                    \
        libldap2-dev                  \
        libx11-dev"

ARG TOOLS="                           \
        ca-certificates               \
        default-libmysqlclient-dev    \
        openssh-client                \
        sshpass                       \
        bubblewrap"

ARG APT_MIRROR=http://mirrors.ustc.edu.cn
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked,id=core \
    --mount=type=cache,target=/var/lib/apt,sharing=locked,id=core \
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

COPY --from=stage-2 /opt /opt
COPY --from=stage-1 /usr/local/bin /usr/local/bin
COPY --from=stage-1 /opt/jumpserver/apps/libs/ansible/ansible.cfg /etc/ansible/

WORKDIR /opt/jumpserver

ARG VERSION
ENV VERSION=$VERSION

VOLUME /opt/jumpserver/data

ENTRYPOINT ["./entrypoint.sh"]

EXPOSE 8080

STOPSIGNAL SIGQUIT

CMD ["start", "all"]
