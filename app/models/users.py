from peewee import AutoField, CharField, BooleanField
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import BaseModel


class Users(BaseModel, UserMixin):
    id = AutoField()
    username = CharField(unique=True)
    password = CharField()
    is_admin = BooleanField(default=False)

    @property
    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
