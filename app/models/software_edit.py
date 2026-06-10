from peewee import CharField, TextField
from . import PersistentBaseModel


class SoftwareEdit(PersistentBaseModel):
    software_name = CharField(primary_key=True)
    description = TextField(null=True, default=None)
    web_page = TextField(null=True, default=None)
    documentation = TextField(null=True, default=None)
    use_link = TextField(null=True, default=None)
    ai_description = TextField(null=True, default=None)
    ai_software_type = TextField(null=True, default=None)
    ai_software_class = TextField(null=True, default=None)
    ai_research_field = TextField(null=True, default=None)
    ai_research_area = TextField(null=True, default=None)
    ai_research_discipline = TextField(null=True, default=None)
    ai_core_features = TextField(null=True, default=None)
    ai_general_tags = TextField(null=True, default=None)
    ai_example_use = TextField(null=True, default=None)
    auto_values = TextField(null=True, default=None)
    edited_at = TextField(null=True, default=None)
    edited_by = TextField(null=True, default=None)
