#!/bin/bash
#


# Run redis
docker run --name redis -d redis

# Run jumpserver
docker run -d --name jumpserver -p 8080:8080 --link redis:redis jumpserver/jumpserver:v0.4.0-beta1

# Finished
echo -e "Please visit http://ServerIP:8080\n Username: admin\nPassword: admin\n"