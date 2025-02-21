#!/bin/bash

# 配置参数
API_URL=${API_URL:-"http://127.0.0.1:8080"}
KEY_ID=${API_KEY_ID:-"72b0b0aa-ad82-4182-a631-ae4865e8ae0e"}
KEY_SECRET=${API_KEY_SECRET:-"6fuSO7P1m4cj8SSlgaYdblOjNAmnxDVD7tr8"}
ORG_ID=${ORG_ID:-"00000000-0000-0000-0000-000000000002"}

# 查询参数
ASSET="ubuntu_docker"
ACCOUNT="root"
QUERY_STRING="asset=${ASSET}&account=${ACCOUNT}"

# 计算时间戳
DATE=$(date -u +"%a, %d %b %Y %H:%M:%S GMT")

# 计算 (request-target) 需要包含查询参数
REQUEST_TARGET="get /api/v1/accounts/integration-applications/account-secret/?${QUERY_STRING}"

# 生成签名字符串
SIGNING_STRING="(request-target): $REQUEST_TARGET
accept: application/json
date: $DATE
x-jms-org: $ORG_ID"

# 计算 HMAC-SHA256 签名
SIGNATURE=$(echo -n "$SIGNING_STRING" | openssl dgst -sha256 -hmac "$KEY_SECRET" -binary | base64)

# 发送请求
curl -G "$API_URL/api/v1/accounts/integration-applications/account-secret/" \
    -H "Accept: application/json" \
    -H "Date: $DATE" \
    -H "X-JMS-ORG: $ORG_ID" \
    -H "X-Source: jms-pam" \
    -H "Authorization: Signature keyId=\"$KEY_ID\",algorithm=\"hmac-sha256\",headers=\"(request-target) accept date x-jms-org\",signature=\"$SIGNATURE\"" \
    --data-urlencode "asset=$ASSET" \
    --data-urlencode "account=$ACCOUNT"