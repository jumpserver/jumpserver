FROM alpine
MAINTAINER xRain <xrain@simcu.com>
RUN apk add --update openssh sshpass python py-mysqldb py-psutil py-crypto && \
	rm -rf /var/cache/apk/* 
COPY . /jumpserver
WORKDIR /jumpserver
RUN python /jumpserver/install/docker/get-pip.py && \
 	pip install -r /jumpserver/install/docker/piprequires.txt && \
	 rm -rf /jumpserver/docs && \
 	cp /jumpserver/install/docker/run.sh /run.sh && \
  	rm -rf /etc/motd && chmod +x /run.sh && \
  	rm -rf /jumpserver/keys && \
  	rm -rf /jumpserver/logs && \
  	rm -rf /home && \
  	rm -rf /etc/ssh && \
  	rm -rf /etc/shadow && \
  	rm -rf /etc/passwd && \
  	cp -r /jumpserver/install/docker/useradd /usr/sbin/useradd && \
  	cp -r /jumpserver/install/docker/userdel /usr/sbin/userdel && \
  	chmod +x /usr/sbin/useradd && \
  	chmod +x /usr/sbin/userdel && \
  	mkdir -p /data/home && \
  	mkdir -p /data/logs && \
  	mkdir -p /data/keys && \
  	mkdir -p /data/ssh && \
  	cp -r /jumpserver/install/docker/shadow /data/shadow && \
  	cp -r /jumpserver/install/docker/passwd /data/passwd && \
  	ln -s /data/logs /jumpserver/logs && \
  	ln -s /data/keys /jumpserver/keys && \
  	ln -s /data/home /home && \
  	ln -s /data/ssh /etc/ssh && \
  	ln -s /data/passwd /etc/passwd && \
  	ln -s /data/shadow /etc/shadow && \
  	chmod -R 777 /jumpserver
VOLUME /data
EXPOSE 80 22
CMD /run.sh
