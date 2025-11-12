# SAML SSO Configuration for JumpServer (English)

## SAML Setup

SAML (Security Assertion Markup Language) allows single sign-on with identity providers like Okta or Azure AD.

### General Steps
1. Enable SAML in JumpServer settings.
2. Upload IdP metadata (from your provider).
3. Configure entity ID and ACS URL.
4. Test user login.

### Okta SAML Integration Example
1. In Okta, create a new SAML app.
2. Set **Single sign on URL**: `https://your-jumpserver.com/sso/saml/acs/`
3. Set **Audience URI**: `https://your-jumpserver.com/sso/saml/metadata/`
4. Download IdP metadata and upload to JumpServer → Settings → SSO.
5. Test login via Okta.

For more, see the main Chinese docs: [SAML Guide](saml.md).
