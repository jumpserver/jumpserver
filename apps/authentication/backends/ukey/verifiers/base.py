class BaseVerifier:
    """Verify certificate proofs, without owning users, bindings or sessions."""

    def verify_proof(self, cert, signature, challenge, username=''):
        """Return verified certificate claims or raise UKeyAuthError.

        username is the expected CN for user_sn profiles; certificate-binding
        profiles must resolve application identity from their verified claims.
        """
        raise NotImplementedError
