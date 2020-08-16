from rest_framework import status
from common.exceptions import JMSException


class NodeIsBeingUpdatedByOthers(JMSException):
    status_code = status.HTTP_409_CONFLICT
