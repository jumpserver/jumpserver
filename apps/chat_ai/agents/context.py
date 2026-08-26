from dataclasses import dataclass


@dataclass(frozen=True)
class RequestAuthContext:
    user_id: str
    org_id: str
    language: str = ''

    @classmethod
    def from_request(cls, request, org_id):
        return cls(
            user_id=str(request.user.id),
            org_id=str(org_id),
            language=getattr(request, 'LANGUAGE_CODE', ''),
        )

    def headers(self):
        headers = {'X-JMS-ORG': self.org_id, 'Accept': 'application/json'}
        if self.language:
            headers['Accept-Language'] = self.language
        return headers
