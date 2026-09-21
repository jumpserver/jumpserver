## DBX

Lightweight cross-platform database client, supports MySQL, MariaDB, PostgreSQL, Oracle, SQLServer, Dameng, ClickHouse, MongoDB and Redis.

### Components

The application and the drivers ship in one package, extracted to `C:\Program Files\DBX`:

- Application: `C:\Program Files\DBX\DBX.exe`, use the global environment variable `DBX_HOME` to specify another install directory
- Drivers: `C:\Program Files\DBX\agents`, contains JRE 21 and the Oracle, Dameng drivers, use the global environment variable `DBX_DRIVERS_HOME` to specify another directory

MySQL, MariaDB, PostgreSQL, SQLServer, ClickHouse, MongoDB and Redis use the drivers built into DBX and need no extra component. For Oracle and Dameng, the driver is copied from the install directory into the current session user directory on connect and the JRE is used in place, no internet access required.

### Notes

- Use the global environment variable `DBX_CLEAN_HOME_AT_CLOSE` to control whether application data is cleaned on exit, defaults to `true`
- The drivers must match the application version, both are released in the same package
- The packages are served by the JumpServer download site, the applet host only needs to reach JumpServer itself and requires no internet access
- The driver package also contains the DB2 driver, but the connection deep link of DBX 0.6.17 does not support the db2 type yet, so it is not listed in the supported protocols
- The connection URL carries no password. The applet fills it into the connection dialog and clears "save password", so it stays out of the command line and out of the stored connection. If filling fails, the applet falls back to a URL that carries the password
- The interface language follows the user's language setting in JumpServer regardless of the applet host Windows language, and falls back to English when DBX has no matching locale
- Whether Oracle connects as sysdba comes from the use_sysdba connect option, falling back to the privileged account flag when the option is absent
- SSL connection is not supported yet
