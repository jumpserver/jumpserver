from django.utils.translation import gettext_lazy as _

# JumpServer
JMS_USERNAME = "jms_username"

# ASSENT
JMS_ASSET_ID = "jms_asset.id"
JMS_ASSET_TYPE = "jms_asset.type"
JMS_ASSET_CATEGORY = "jms_asset.category"
JMS_ASSET_PROTOCOL = "jms_asset.protocol"
JMS_ASSET_PORT = "jms_asset.port"
JMS_ASSET_NAME = "jms_asset.name"
JMS_ASSET_ADDRESS = "jms_asset.address"

# Account
JMS_ACCOUNT_ID = "jms_account.id"
JMS_ACCOUNT_USERNAME = "jms_account.name"

# JOB
JMS_JOB_ID = "jms_job_id"
JMS_JOB_NAME = "jms_job_name"

JMS_JOB_VARIABLE_HELP = {
    JMS_USERNAME: _('The current user`s username of JumpServer'),
    JMS_ASSET_ID: _('The id of the asset in the JumpServer'),
    JMS_ASSET_TYPE: _('The type of the asset in the JumpServer'),
    JMS_ASSET_CATEGORY: _('The category of the asset in the JumpServer'),
    JMS_ASSET_NAME: _('The name of the asset in the JumpServer'),
    JMS_ASSET_ADDRESS: _('Address used to connect this asset in JumpServer'),
    JMS_ASSET_PORT: _('Port used to connect this asset in JumpServer'),
    JMS_JOB_ID: _('ID of the job'),
    JMS_JOB_NAME: _('Name of the job'),
}
