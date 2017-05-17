FROM jumpserver/alpine-py3:v3.4
LABEL MAINTAINER Jumpserver Team <ibuler@qq.com>

COPY . /opt/jumpserver
COPY config_docker.py /opt/jumpserver/config.py
WORKDIR /opt/jumpserver
RUN rm -r .git
RUN rm -f config.py

VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

RUN ln -s /usr/bin/pip3 /usr/bin/pip
RUN ln -s /usr/bin/python3 /usr/bin/python
RUN cp config_docker.py config.py

RUN pip install -r requirements/requirements.txt
RUN cd utils && sh make_migrations.sh && sh init_db.sh
EXPOSE 8080
CMD python run_server.py
