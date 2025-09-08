TEMPLATE_META = [
    {
        "template_name": "authentication/_msg_different_city.html",
        "label": "异地登录提醒邮件模板",
        "context": ["subject", "name", "username", "ip", "time", "city"],
        "context_example": [
            {"key": "subject", "label": "邮件主题", "example": "异地登录提醒"},
            {"key": "name", "label": "用户显示名", "example": "zhangsan"},
            {"key": "username", "label": "登录用户名", "example": "zhangsan"},
            {"key": "ip", "label": "登录 IP", "example": "8.8.8.8"},
            {"key": "time", "label": "发生时间", "example": "2025-09-04 10:00:00"},
            {"key": "city", "label": "城市", "example": "洛杉矶"},
        ]
    },
    {
        "template_name": "authentication/_msg_oauth_bind.html",
        "label": "第三方账号绑定提醒邮件模板",
        "context": ["subject", "name", "username", "ip", "time", "oauth_name", "oauth_id"],
        "context_example": [
            {"key": "subject", "label": "邮件主题", "example": "WeCom 绑定提醒"},
            {"key": "name", "label": "用户显示名", "example": "zhangsan"},
            {"key": "username", "label": "登录用户名", "example": "zhangsan"},
            {"key": "ip", "label": "请求 IP", "example": "8.8.8.8"},
            {"key": "time", "label": "发生时间", "example": "2025-09-04 10:00:00"},
            {"key": "oauth_name", "label": "第三方服务名", "example": "WeCom"},
            {"key": "oauth_id", "label": "第三方账号 ID", "example": "000000"},
        ]
    },
    {
        "template_name": "authentication/_msg_reset_password_code.html",
        "label": "重置密码验证码邮件模板",
        "context": ["user", "title", "code"],
        "context_example": [
            {"key": "user", "label": "用户对象（可为用户名字符串或 user 实例）", "example": "zhangsan"},
            {"key": "title", "label": "邮件标题", "example": "Jumpserver: 忘记密码"},
            {"key": "code", "label": "验证码", "example": "123456"},
        ]
    },
    {
        "template_name": "authentication/_msg_mfa_email_code.html",
        "label": "Email MFA 验证码邮件模板",
        "context": ["user", "title", "code"],
        "context_example": [
            {"key": "user", "label": "用户对象（可为用户名字符串或 user 实例）", "example": "zhangsan"},
            {"key": "title", "label": "邮件标题", "example": "Jumpserver: MFA code"},
            {"key": "code", "label": "验证码", "example": "654321"},
        ]
    },
    {
        "template_name": "ops/_msg_terminal_performance.html",
        "label": "组件性能告警邮件模板",
        "context": ["terms_with_errors"],
        "context_example": [
            {"key": "terms_with_errors", "label": "检测项与错误信息列表",
             "example": "[[\"server1\", [\"CPU 过高\", \"内存不足\"]], [\"server2\", [\"磁盘空间不足\"]]]"}
        ]
    },
    {
        "template_name": "users/_msg_user_created.html",
        "label": "用户创建通知邮件模板",
        "context": ["subject", "honorific", "content", "user", "rest_password_url", "rest_password_token",
                    "forget_password_url", "login_url"],
        "context_example": [
            {"key": "subject", "label": "邮件主题", "example": "欢迎注册"},
            {"key": "honorific", "label": "称呼", "example": "尊敬的用户"},
            {"key": "content", "label": "邮件正文模板内容", "example": "您的账号已创建"},
            {"key": "user", "label": "用户对象或用户名", "example": "zhangsan"},
            {"key": "rest_password_url", "label": "重置密码链接", "example": "https://jumpserver/reset-password"},
            {"key": "rest_password_token", "label": "重置密码 token", "example": "token123"},
            {"key": "forget_password_url", "label": "忘记密码页面链接",
             "example": "https://jumpserver/forgot-password"},
            {"key": "login_url", "label": "登录链接", "example": "https://jumpserver/login"},
        ]
    },
    {
        "template_name": "authentication/_msg_reset_password.html",
        "label": "重置密码邮件模板（含链接）",
        "context": ["user", "rest_password_url", "rest_password_token", "forget_password_url", "login_url"],
        "context_example": [
            {"key": "user", "label": "用户对象或用户名", "example": "zhangsan"},
            {"key": "rest_password_url", "label": "重置密码链接", "example": "https://jumpserver/reset-password"},
            {"key": "rest_password_token", "label": "重置密码 token", "example": "token123"},
            {"key": "forget_password_url", "label": "忘记密码页面链接",
             "example": "https://jumpserver/forgot-password"},
            {"key": "login_url", "label": "登录链接", "example": "https://jumpserver/login"},
        ]
    },
    {
        "template_name": "authentication/_msg_rest_password_success.html",
        "label": "密码重置成功通知邮件模板",
        "context": ["name", "ip_address", "browser"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "ip_address", "label": "请求 IP", "example": "192.168.1.1"},
            {"key": "browser", "label": "浏览器 UA", "example": "Chrome"},
        ]
    },
    {
        "template_name": "authentication/_msg_rest_public_key_success.html",
        "label": "公钥重置成功通知邮件模板",
        "context": ["name", "ip_address", "browser"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "ip_address", "label": "请求 IP", "example": "192.168.1.1"},
            {"key": "browser", "label": "浏览器 UA", "example": "Chrome"},
        ]
    },
    {
        "template_name": "users/_msg_password_expire_reminder.html",
        "label": "密码即将过期提醒邮件模板",
        "context": ["name", "date_password_expired", "update_password_url", "forget_password_url", "email",
                    "login_url"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "date_password_expired", "label": "密码过期时间（本地时区）", "example": "2025-09-30 23:59:59"},
            {"key": "update_password_url", "label": "修改密码页面链接",
             "example": "https://jumpserver/ui/#/profile/index"},
            {"key": "forget_password_url", "label": "忘记密码页面链接",
             "example": "https://jumpserver/forgot-password"},
            {"key": "email", "label": "用户邮箱", "example": "zhangsan@example.com"},
            {"key": "login_url", "label": "登录链接", "example": "https://jumpserver/login"},
        ]
    },
    {
        "template_name": "users/_msg_account_expire_reminder.html",
        "label": "账号即将过期提醒邮件模板",
        "context": ["name", "date_expired"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "date_expired", "label": "账号过期时间", "example": "2025-09-30 23:59:59"},
        ]
    },
    {
        "template_name": "users/_msg_reset_ssh_key.html",
        "label": "SSH Key 重置通知邮件模板",
        "context": ["name", "url"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "url", "label": "修改 SSH Key 链接",
             "example": "https://jumpserver/ui/#/profile/password-and-ssh-key/?tab=SSHKey"},
        ]
    },
    {
        "template_name": "users/_msg_reset_mfa.html",
        "label": "MFA 重置通知邮件模板",
        "context": ["name", "url"],
        "context_example": [
            {"key": "name", "label": "用户名或显示名", "example": "zhangsan"},
            {"key": "url", "label": "启用 MFA 链接", "example": "https://jumpserver/user-otp-enable-start"},
        ]
    }
]
