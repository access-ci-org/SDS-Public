from peewee import AutoField, DateTimeField, TextField, CharField, IntegerField, BooleanField
from . import BaseModel


class UserReports(BaseModel):

    REPORT_TYPES = [("report", "Report"), ("feedback", "Feedback")]

    id = AutoField()
    datetime = DateTimeField()
    element_text = TextField(default="")
    row_name = CharField(default="")
    row_index = IntegerField(default="")
    column_name = CharField(default="")
    column_index = IntegerField(default="")
    user_message = TextField(default="")
    report_type = CharField(choices=REPORT_TYPES)
    resolved = BooleanField(default=False)
