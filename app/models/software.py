from peewee import AutoField, CharField, SQL, TextField
from . import BaseModel


class Software(BaseModel):
    id = AutoField()
    software_name = CharField(unique=True, constraints=[SQL("COLLATE NOCASE")])
    software_description = TextField(default="")
    software_web_page = CharField(default="")  # Link to the software's main webpage
    software_documentation = CharField(
        default=""
    )  # Link to the software's main documentation page
    software_use_link = CharField(default="")  # Link to examples of software being used
