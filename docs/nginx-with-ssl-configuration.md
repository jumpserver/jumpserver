# 使用Nginx搭建SSL配置

跳板机是所有服务器的入口，所以，它的安全至关重要。因此，建议把`Jumpserver`搭建在内网环境中，并且加上SSL证书，保证数据传输的安全。

## nginx的安装

不同的操作系统及版本，安装方法都不太一样。我们以`Debian`为例。

```
apt-get update
apt-get install -y nginx
```

更多安装示例请参考 [Nginx官方安装指南](https://www.nginx.com/resources/wiki/start/topics/tutorials/install/)

## Nginx中的SSL的配置

* 编辑 `/etc/nginx/sites-enabled/default` 或者指定的`Jumpserver`的配置文件

* 示例如下

```
server {
  listen              443;
  listen              80;
  server_name         YOUR_DOMAIN;
  ssl_certificate     YOUR_DOMAIN_CRT;
  ssl_certificate_key YOUR_DOMAIN_KEY;
  ssl_protocols	TLSv1 TLSv1.1 TLSv1.2;
  ssl_ciphers	HIGH:!aNULL:!MD5;
  ssl_prefer_server_ciphers on;
  ssl on ;

  if ($ssl_protocol = "") {
    rewrite ^ https://$host$request_uri? permanent;
  }

  location / {
    proxy_set_header Connection "";
    proxy_http_version 1.1;
    proxy_pass      http://JUMPSERVER_HOST:WEB_PORT;
  }

  location /_ws/ {
    keepalive_timeout 600s;
    send_timeout 600s;
    proxy_connect_timeout 7d;
    proxy_send_timeout 7d;
    proxy_read_timeout 7d;
    rewrite ^/_ws(/.*)$ $1 break;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass      http://JUMPSERVER_HOST:WS_PORT;
  }
}

```

* 请替换如下表格的关键字


关键字  		 		| 示例          					| 说明
------------- 		| -------------					|-------
`YOUR_DOMAIN`  		|  example.com 					| `Jumpserver`的域名
`YOUR_DOMAIN_CRT`  	| /etc/nginx/certs/example.crt	| SSL证书的CRT文件
`YOUR_DOMAIN_KEY`  	| /etc/nginx/certs/example.key	| SSL证书的KEY文件
`JUMPSERVER_HOST`  	| 127.0.0.1						| `Jumpserver`服务器IP
`WEB_PORT ` 		| 80							| `Jumpserver`网页监听端口
`WS_PORT `  		| 3000							| websocket端口，`Jumpserver` 默认为3000

* 此配置会强制使用`https`, 建议加上(即if判断的那三行)。