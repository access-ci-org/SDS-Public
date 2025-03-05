from peewee import AutoField, ForeignKeyField, TextField
from . import BaseModel
from .software import Software
from .resource import Resource


class SoftwareResource(BaseModel):
    id = AutoField()
    software_id = ForeignKeyField(Software)
    resource_id = ForeignKeyField(Resource)
    software_version = TextField(default="")

    class Meta:
        # There should only be one row with a specific resource_id and software_id combination
        indexes = ((("software_id", "resource_id"), True),)
