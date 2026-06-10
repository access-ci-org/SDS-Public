from peewee import AutoField, BooleanField, CharField, TextField
from . import PersistentBaseModel


class Banner(PersistentBaseModel):
    id          = AutoField()
    message     = TextField()
    severity    = CharField()
    pages       = CharField()
    is_active   = BooleanField(default=True)
    dismissible = BooleanField(default=True)
    created_at  = TextField()
    created_by  = TextField()
    updated_at  = TextField(null=True, default=None)
