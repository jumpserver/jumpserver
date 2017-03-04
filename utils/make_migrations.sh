#!/bin/bash
#

python2.7 ../apps/manage.py makemigrations

python2.7 ../apps/manage.py migrate
