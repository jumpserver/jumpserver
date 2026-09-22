from ...common.abstract_model import AbstractModel


class Platform(AbstractModel):
    _fields = {
        'Id': ('id', None), 'Name': ('name', None),
        'Category': ('category', None), 'Type': ('type', None),
    }
    _required = ('Id', 'Name', 'Category', 'Type')


class Asset(AbstractModel):
    _fields = {
        'Id': ('id', None), 'Name': ('name', None),
        'Address': ('address', None), 'Platform': ('platform', Platform),
    }
    _required = ('Id', 'Name', 'Address', 'Platform')


class Account(AbstractModel):
    _fields = {
        'Id': ('id', None), 'Name': ('name', None),
        'Username': ('username', None), 'SecretType': ('secret_type', None),
        'Secret': ('secret', None),
    }
    _required = ('Id', 'Name', 'Username', 'SecretType', 'Secret')


class CredentialState(AbstractModel):
    _fields = {
        'Key': ('key', None), 'Revision': ('revision', None),
        'AccountId': ('account_id', None),
    }
    _required = ('Key', 'Revision', 'AccountId')


class GetCredentialRequest(AbstractModel):
    _fields = {'Key': ('key', None), 'AccountId': ('account_id', None)}

    def _validate(self):
        super()._validate()
        if bool(self.Key) == bool(self.AccountId):
            raise ValueError('exactly one of Key or AccountId is required')
        return self


class GetCredentialResponse(AbstractModel):
    _fields = {
        'Key': ('key', None), 'Revision': ('revision', None),
        'Asset': ('asset', Asset), 'Account': ('account', Account),
    }
    _required = ('Key', 'Revision', 'Asset', 'Account')


class ConfirmCredentialRequest(CredentialState):
    pass


class ConfirmCredentialResponse(AbstractModel):
    _fields = {'Key': ('key', None), 'Revision': ('revision', None)}
    _required = ('Key', 'Revision')


class CredentialRevision(AbstractModel):
    _fields = {
        'Key': ('key', None), 'Revision': ('revision', None),
        'Available': ('available', None), 'Changed': ('changed', None),
    }
    _required = ('Key', 'Revision', 'Available', 'Changed')


class KnownCredentialRevision(AbstractModel):
    _fields = {'Key': ('key', None), 'Revision': ('revision', None)}
    _required = ('Key', 'Revision')


class AgentSyncRequest(AbstractModel):
    _fields = {
        'ConfigDigest': ('config_digest', None),
        'Credentials': ('credentials', [KnownCredentialRevision]),
        'DeliveredCredentials': ('delivered_credentials', [KnownCredentialRevision]),
        'SyncStatus': ('sync_status', None), 'SyncError': ('sync_error', None),
    }
    _required = ('Credentials', 'DeliveredCredentials')


class AgentSyncResponse(AbstractModel):
    _fields = {
        'ConfigDigest': ('config_digest', None),
        'Configuration': ('configuration', None),
        'Credentials': ('credentials', [CredentialRevision]),
        'RemovedKeys': ('removed_keys', None),
        'DateLastSynced': ('date_last_synced', None),
    }
    _required = ('ConfigDigest', 'Credentials', 'RemovedKeys', 'DateLastSynced')
