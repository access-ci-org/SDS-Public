from peewee import AutoField, ForeignKeyField, TextField
from . import BaseModel
from .software import Software


class AISoftwareInfo(BaseModel):
    id = AutoField()
    software_id = ForeignKeyField(Software, unique=True)
    ai_description = TextField(default="")
    ai_software_type = TextField(default="")
    ai_software_class = TextField(default="")
    ai_research_field = TextField(default="")
    ai_research_area = TextField(default="")
    ai_research_discipline = TextField(default="")
    ai_core_features = TextField(default="")
    ai_general_tags = TextField(default="")
    ai_example_use = TextField(default="")
