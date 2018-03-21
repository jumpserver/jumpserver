#!/bin/bash
#

python3 ../apps/manage.py makemigrations

python3 ../apps/manage.py migrate
