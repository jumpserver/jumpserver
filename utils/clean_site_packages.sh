#!/bin/bash
#

lib_path="/opt/py3/lib/python3.11/site-packages"

# 清理不需要的模块
need_clean="jedi botocore/data"
for i in $need_clean; do
  rm -rf "${lib_path}/${i}"
done

# 清理 ansible connection 中 不需要的模块
ansible_connection="${lib_path}/ansible_collections"
need_clean="fortinet dellemc f5networks netapp theforeman google azure cyberark ibm
            netbox purestorage inspur netapp_eseries sensu check_point vyos arista"
for i in $need_clean; do
  echo "rm -rf ${ansible_connection:-tmp}/${i}"
  rm -rf "${ansible_connection:-tmp}/${i}"
done

# 清理缓存文件
cd lib_path
find . -name "*.pyc" -exec rm -f {} \;

# 清理不需要的国际化文件
find . -name 'locale' -o -name 'locales' -type d | while read -r dir; do
    find "$dir" -mindepth 1 -maxdepth 1 -type d \
      ! -name 'zh_Hans' \
      ! -name 'zh_Hant' \
      ! -name 'zh_CN' \
      ! -name 'en' \
      ! -name 'en_US' \
      ! -name 'ja' \
      ! -name 'fr' \
      -exec rm -rf {} \;
done
