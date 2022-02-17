#!/bin/bash

echo "安装依赖"
brew install libtiff libjpeg webp little-cms2 openssl gettext git git-lfs mysql libxml2 libxmlsec1 pkg-config

echo "安装依赖的插件"
git lfs install
