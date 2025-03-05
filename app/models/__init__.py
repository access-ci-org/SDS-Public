from pathlib import Path
from peewee import SqliteDatabase, Model

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = Path.cwd()
db_path = BASE_DIR / "sqlite_db.db"
db = SqliteDatabase(db_path)


class BaseModel(Model):
    class Meta:
        database = db
