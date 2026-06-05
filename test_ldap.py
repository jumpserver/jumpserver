import ldap

print(ldap.__version__)

print(ldap.get_option(ldap.OPT_API_INFO))
print(hex(ldap.OPT_X_TLS_CACERTFILE))
print(ldap.OPT_X_TLS_CACERTFILE)
ldap.set_option(
    ldap.OPT_X_TLS_CACERTFILE,
    "/Users/nut/ldap-test/certs/ca.crt"
)
ldap.set_option(
    ldap.OPT_X_TLS_CERTFILE,
    "/Users/nut/ldap-test/certs/client.crt"
)
ldap.set_option(
    ldap.OPT_X_TLS_KEYFILE,
    "/Users/nut/ldap-test/certs/client.key"
)
ldap.set_option(
    ldap.OPT_X_TLS_REQUIRE_CERT,
    ldap.OPT_X_TLS_DEMAND
)
ldap.set_option(ldap.OPT_X_TLS_NEWCTX, 0)

conn = ldap.initialize("ldap://127.0.0.1:389")
conn.start_tls_s()
