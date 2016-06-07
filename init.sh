#!/bin/sh
#

trap '' SIGINT
base_dir=$(dirname $0)

export LANG='zh_CN.UTF-8'
python $base_dir/connect.py

exit
