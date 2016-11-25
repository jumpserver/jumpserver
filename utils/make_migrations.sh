#!/bin/bash
#

python ../apps/manage.py makemigrations

python ../apps/manage.py migrate
