# Azure AD SAML SSO for JumpServer (Lab/Dev Environment)
# Free Azure AD trial tenant — zero production risk
# Example Tenant ID: 2745f97e-08e6-4b97-849a-b78b930ee3a8

from .config_default import *  # noqa 

SAML_AUTH = True
SAML_METADATA_URL = "https://login.microsoftonline.com/{TENANT_ID}/federationmetadata/2007-06/federationmetadata.xml"
SAML_ENTITY_ID = "https://jumpserver.local/saml/metadata"
SAML_ORG_NAME = "PhD Cybersecurity Lab"
SAML_CONTACT_EMAIL = "manjula101@proton.me"
SAML_ATTRIBUTE_MAPPING = {
    'username': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier',
    'email': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
    'name': 'http://schemas.microsoft.com/identity/claims/displayname',
}
