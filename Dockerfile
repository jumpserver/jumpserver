FROM jumpserver/core-base:20241210_070105 AS stage-build

ARG VERSION

WORKDIR /opt/jumpserver

ADD . .

RUN echo > /opt/jumpserver/config.yml \
    && \
    if [ -n "${VERSION}" ]; then \
        sed -i "s@VERSION = .*@VERSION = '${VERSION}'@g" apps/jumpserver/const.py; \
    fi

RUN set -ex \
    && export SECRET_KEY=$(head -c100 < /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c 48) \
    && . /opt/py3/bin/activate \
    && cd apps \
    && python manage.py compilemessages


FROM python:3.11-slim-bullseye
ENV LANG=en_US.UTF-8 \
    PATH=/opt/py3/bin:$PATH

ARG DEPENDENCIES="                    \
        libldap2-dev                  \
        libx11-dev"

ARG TOOLS="                           \
        cron                          \
        ca-certificates               \
        default-libmysqlclient-dev    \
        openssh-client                \
        sshpass                       \
        bubblewrap"

ARG APT_MIRROR=http://deb.debian.org

RUN set -ex \
    && sed -i "s@http://.*.debian.org@${APT_MIRROR}@g" /etc/apt/sources.list \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && apt-get update > /dev/null \
    && apt-get -y install --no-install-recommends ${DEPENDENCIES} \
    && apt-get -y install --no-install-recommends ${TOOLS} \
    && mkdir -p /root/.ssh/ \
    && echo "Host *\n\tStrictHostKeyChecking no\n\tUserKnownHostsFile /dev/null\n\tCiphers +aes128-cbc\n\tKexAlgorithms +diffie-hellman-group1-sha1\n\tHostKeyAlgorithms +ssh-rsa" > /root/.ssh/config \
    && echo "no" | dpkg-reconfigure dash \
    && apt-get clean all \
    && rm -rf /var/lib/apt/lists/* \
    && echo "0 3 * * * root find /tmp -type f -mtime +1 -size +1M -exec rm -f {} \; && date > /tmp/clean.log" > /etc/cron.d/cleanup_tmp \
    && chmod 0644 /etc/cron.d/cleanup_tmp

COPY --from=stage-build /opt /opt
COPY --from=stage-build /usr/local/bin /usr/local/bin
COPY --from=stage-build /opt/jumpserver/apps/libs/ansible/ansible.cfg /etc/ansible/

WORKDIR /opt/jumpserver

VOLUME /opt/jumpserver/data

ENTRYPOINT ["./entrypoint.sh"]

EXPOSE 8080

STOPSIGNAL SIGQUIT

CMD ["start", "all"]
