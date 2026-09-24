class BaseVerifier:
    """Verify certificate proofs, without owning users, bindings or sessions."""

    def verify_proof(self, cert, signature, challenge, username=''):
        """Return verified certificate claims or raise UKeyAuthError.

        username is the expected CN for the builtin profile only; it must never
        be used to resolve an external certificate's application identity.
        """
        raise NotImplementedError
