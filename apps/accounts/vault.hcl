ui = true

storage "mysql" {
  address = "127.0.0.1:3306"
  username = "root"
  password = "root"
  database = "jumpserver_yy19"
  table = "vault_data"
}

# 启动
# vault server --log-level=debug -config="/Users/jiangjiebai/vault/config/vault.hcl" -dev
# 如果启动失败，进入数据库删除表 drop table `vault_data`;
