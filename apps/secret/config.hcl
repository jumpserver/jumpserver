ui = true

storage "mysql" {
  address                      = "127.0.0.1:3306"
  username                     = "feng"
  password                     = "root123."
  database                     = "my-vault"
  plaintext_connection_allowed = "true"
}

listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = "true"
}

api_addr     = "http://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"

# 启动
# vault server --log-level=debug -config=config.hcl

# Launch a new terminal session, and set VAULT_ADDR environment variable.
# export VAULT_ADDR='http://127.0.0.1:8200'

# To initialize Vault use secret operator init. This is an unauthenticated request, but it only works on brand new Vaults without existing data:
# vault operator init

# Initialization outputs two incredibly important pieces of information: the unseal keys and the initial root token.
# This is the only time ever that all of this data is known by Vault, and also the only time that the unseal keys should ever be so close together.

# Begin unsealing the Vault:
# vault operator unseal

# Unseal Key 1: k/y6vsrEfZuY8ku/aCO+QRsPVSUhDbTbFt5XXZpGZP8N
# Unseal Key 2: 4PRqjx4JPTJIiEA2SYDToGWn0UeN+rcJ8cGd+I3wD3AJ
# Unseal Key 3: db+XoTa1OKszCyvcV3g9tW7kAXpwFD4HUBECL03VKPxT
# Unseal Key 4: fbm972FTVfSPtRO8Ne8UMGWJajM9s+yVjYwdyWYmJy4M
# Unseal Key 5: jAyW+Jq79LF95Br8z5VUX6bQPwLK7BAUg5Flw1oGAZ4P
#
# Initial Root Token: s.JqVYFWIrtPzctcePjaWTtxXf
