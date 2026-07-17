from peewee import (
    AutoField,
    BooleanField,
    ForeignKeyField,
    IntegerField,
    TextField,
)
from . import BaseModel
from .softwareResource import SoftwareResource


class SoftwareResourceCommand(BaseModel):
    id = AutoField()
    software_resource_id = ForeignKeyField(
        SoftwareResource, backref="load_commands", on_delete="CASCADE"
    )
    # full module name as spider reports it, e.g. "proj/8.1.1"
    module_name = TextField(default="")
    # modules that must be loaded first, space-separated in load order;
    # empty when the module is directly loadable
    parent_chain = TextField(default="")
    # complete runnable command, e.g. "module load gcc/11.2.0 proj/8.1.1"
    command = TextField(default="")
    # True when the chain goes through a hidden module (dot-prefixed version)
    hidden = BooleanField(default=False)

    # Derived display state, written only by the chain-edit projection
    # (app/logic/chain_projection.py); the columns above are collected
    # facts the projection never mutates.
    #
    # admin chose to hide this command from display
    suppressed = BooleanField(default=False)
    # admin replacement text; display shows COALESCE(display_command, command)
    display_command = TextField(null=True, default=None)
    # 0 = shown first; NULL = not displayed
    display_rank = IntegerField(null=True, default=None)
    # row materialized from an admin-added command edit rather than collected
    admin_added = BooleanField(default=False)

    class Meta:
        # One row per distinct command for a software/resource/version entry
        indexes = ((("software_resource_id", "command"), True),)
