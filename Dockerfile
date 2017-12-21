FROM jumpserver/python:3
MAINTAINER Jumpserver Team <ibuler@qq.com>


COPY . /opt/jumpserver
WORKDIR /opt/jumpserver

RUN yum -y install epel-release && yum clean all -y
RUN cd requirements && yum -y install $(cat rpm_requirements.txt) && yum clean all -y
RUN cd requirements && pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN rm -r .git
RUN rm -f config.py

VOLUME /opt/jumpserver/data
VOLUME /opt/jumpserver/logs

RUN cp config_docker.py config.py

EXPOSE 8080
CMD cd utils && sh make_migrations.sh && sh init_db.sh && cd .. && python run_server.py
