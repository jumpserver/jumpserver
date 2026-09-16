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
    _fields = {'Key': ('key', None)}
    _required = ('Key',)


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


class HeartbeatRequest(AbstractModel):
    _fields = {'Credentials': ('credentials', [CredentialState])}
    _required = ('Credentials',)


class HeartbeatError(AbstractModel):
    _fields = {
        'Key': ('key', None), 'Code': ('code', None), 'Detail': ('detail', None),
    }
    _required = ('Key', 'Code', 'Detail')


class HeartbeatResponse(AbstractModel):
    _fields = {
        'Updated': ('updated', None), 'Errors': ('errors', [HeartbeatError]),
        'DateLastSeen': ('date_last_seen', None),
    }
    _required = ('Updated', 'Errors', 'DateLastSeen')


class SubscribeEventsRequest(AbstractModel):
    _fields = {'Enabled': ('enabled', None)}
    _required = ('Enabled',)


class SubscribeEventsResponse(AbstractModel):
    _fields = {'Enabled': ('enabled', None)}
    _required = ('Enabled',)


class PollEventsRequest(AbstractModel):
    pass


class Event(AbstractModel):
    _fields = {
        'DeliveryId': ('delivery_id', None), 'AttemptId': ('attempt_id', None),
        'EventId': ('event_id', None), 'Event': ('event', None),
        'InstanceId': ('instance_id', None), 'ClientId': ('client_id', None),
        'ConfigurationId': ('configuration_id', None), 'Key': ('key', None),
        'Revision': ('revision', None), 'OccurredAt': ('occurred_at', None),
    }
    _required = ('DeliveryId', 'AttemptId', 'EventId', 'Event', 'InstanceId', 'ClientId')


class PollEventsResponse(AbstractModel):
    _fields = {'Enabled': ('enabled', None), 'Events': ('events', [Event])}
    _required = ('Enabled', 'Events')


class ReportEventRequest(AbstractModel):
    _fields = {
        'AttemptId': ('attempt_id', None), 'Result': ('result', None),
        'StatusCode': ('status_code', None), 'Reason': ('reason', None),
    }
    _required = ('AttemptId', 'Result')


class ReportEventResponse(AbstractModel):
    _fields = {'Result': ('result', None)}
    _required = ('Result',)
