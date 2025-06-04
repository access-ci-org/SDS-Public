from peewee import AutoField, ForeignKeyField, TextField
from . import BaseModel
from .software import Software
from .resource import Resource


class SoftwareResource(BaseModel):
    id = AutoField()
    software_id = ForeignKeyField(Software)
    resource_id = ForeignKeyField(Resource)
    # software versions and command from lmod only
    software_version = TextField(default="")
    command = TextField(default="")

    class Meta:
        # There should only be one row with a specific resource_id, software_id, and version combination
        indexes = ((("software_id", "resource_id", "software_version"), True),)
