class Credential:
    def __init__(self, app_id, app_secret):
        if not app_id or not app_secret:
            raise ValueError('app_id and app_secret are required')
        self.AppId = app_id
        self.AppSecret = app_secret
