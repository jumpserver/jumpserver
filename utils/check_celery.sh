#!/bin/bash

if [[ "$(ps axu | grep 'celery' | grep -v 'grep' | grep -cv 'defunct')" -gt "2" ]];then
  exit 0
else
  exit 1
fi