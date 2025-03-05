from peewee import AutoField, ForeignKeyField, TextField
from . import BaseModel
from .software import Software
from .containers import Container


class SoftwareContainer(BaseModel):
    id = AutoField()
    software_id = ForeignKeyField(Software, backref='containers')
    container_id = ForeignKeyField(Container, backref='software')
    # resource_id = ForeignKeyField(Resource)
    software_versions = TextField(default="")

    class Meta:
        # There should only be one row with a specific software_id, container_id and resource_id combination
        indexes = ((("software_id", "container_id"), True),)
