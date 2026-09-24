DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000002'


class ClientProfile:
    def __init__(
        self, endpoint='', org_id=DEFAULT_ORG_ID, configuration_id=None,
        timeout=10, source='jms-pam',
    ):
        if not endpoint:
            raise ValueError('endpoint is required')
        self.Endpoint = endpoint.rstrip('/')
        self.OrgId = org_id
        self.ConfigurationId = configuration_id
        self.Timeout = timeout
        self.Source = source
