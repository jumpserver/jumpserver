from jms_pam import JumpServerPAMClient


client = JumpServerPAMClient.from_config('jms-pam.json')

credential = client.get_credential('cred-pg-main')

# 使用 credential.username 和 credential.secret 创建并验证新连接，
# 再关闭旧连接池。成功后才确认应用已经使用这个版本。
client.confirm_applied(credential)
