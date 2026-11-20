## DBX

轻量级跨平台数据库客户端，支持 MySQL、MariaDB、PostgreSQL、Oracle、SQLServer、达梦、ClickHouse、MongoDB、Redis，以及 OceanBase 的 MySQL 租户和 Oracle 租户。

### 组成

主程序、驱动与 WebView2 安装器在同一个安装包内，解压到 `C:\Program Files\DBX`：

- 主程序：`C:\Program Files\DBX\DBX.exe`，可通过全局环境变量 `DBX_HOME` 指定其他安装目录
- 驱动：`C:\Program Files\DBX\agents`，含 JRE 21 与 Oracle、达梦、OceanBase Oracle 租户等驱动，可通过全局环境变量 `DBX_DRIVERS_HOME` 指定其他目录
- WebView2：`C:\Program Files\DBX\webview2`，DBX 依赖的 Microsoft Edge WebView2 Runtime 离线安装器，部署应用时自动执行，日志写在同目录的 `install.log`，发布机无需另行安装；已装有可用运行时（包括更新的版本）的发布机不受影响

MySQL、MariaDB、PostgreSQL、SQLServer、ClickHouse、MongoDB、Redis 与 OceanBase 的 MySQL 租户使用 DBX 内置驱动，无需额外组件；Oracle、达梦、OceanBase 的 Oracle 租户连接时会自动从安装目录复制驱动到当前会话用户目录，JRE 直接使用安装目录中的那份，均无需联网下载。

### 说明

- 通过全局环境变量 `DBX_CLEAN_HOME_AT_CLOSE` 控制退出应用时是否清理应用数据，默认为 `true`
- 主程序与驱动版本需配套，已在同一个安装包内一起发布
- 安装包由 JumpServer 下载站下发，应用发布机只需连通 JumpServer，不需要外网
- 驱动包中另含 DB2 驱动，但 DBX 的连接 deep link 尚不支持 db2 类型，故未在支持协议中开放
- 连接地址不携带密码，密码由应用填入连接对话框并取消勾选保存密码，因此不出现在命令行中，连接配置里也不保留；填入失败时退回携带密码的连接地址
- 界面语言跟随用户在 JumpServer 中设置的语言，与发布机的 Windows 语言无关；DBX 未提供对应语言时使用英文
- Oracle 是否以 sysdba 登录取自连接选项 use_sysdba，没有该选项时按账号是否特权判断
- OceanBase 资产使用 mysql 协议，按平台协议设置中的租户模式分别以 DBX 的 OceanBase、OceanBase Oracle Mode 类型连接；没有租户模式时按 MySQL 租户处理
- 暂不支持 SSL 连接
