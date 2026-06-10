import os
from pathlib import Path


def data_dir() -> Path:
    value = os.environ.get("SDS_DATA_DIR")
    if value:
        return Path(value)
    if Path("data/state").is_dir():
        return Path("data")
    return Path(".")


def state_dir() -> Path:
    return data_dir() / "state"
