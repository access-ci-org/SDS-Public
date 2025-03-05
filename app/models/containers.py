from peewee import AutoField, CharField, ForeignKeyField, TextField
from . import BaseModel
from .resource import Resource


class Container(BaseModel):
    id = AutoField()
    container_name = CharField(default="")
    definition_file = CharField(default="")
    container_file = CharField(default="")
    resource_id = ForeignKeyField(Resource)
    notes = TextField(default="")

    class Meta:
        # There should only be one row with a specific definition_file, container_file
        indexes = ((("container_name", "resource_id"), True),)
