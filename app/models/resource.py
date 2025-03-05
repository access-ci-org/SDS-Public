from peewee import AutoField, CharField
from . import BaseModel


class Resource(BaseModel):
    id = AutoField()
    resource_name = CharField(unique=True)
