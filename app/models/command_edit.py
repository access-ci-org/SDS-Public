from peewee import CharField, TextField, CompositeKey
from . import PersistentBaseModel


class CommandEdit(PersistentBaseModel):
    software_name    = CharField()
    resource_name    = CharField()
    software_version = CharField()
    command          = TextField(null=True, default=None)
    auto_command     = TextField(null=True, default=None)
    edited_at        = TextField(null=True, default=None)
    edited_by        = TextField(null=True, default=None)

    class Meta:
        primary_key = CompositeKey('software_name', 'resource_name', 'software_version')
