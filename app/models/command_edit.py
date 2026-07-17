from peewee import AutoField, BooleanField, CharField, TextField
from . import PersistentBaseModel


class CommandEdit(PersistentBaseModel):
    """One admin edit against one load command of a
    (software, resource, version) entry.

    target_command identifies the auto-collected command the edit applies
    to (SoftwareResourceCommand.command is unique per entry, embeds the
    parent chain, and survives rebuilds as a natural key). A NULL target
    means the row IS the command: an admin-added command whose text lives
    in `replacement`. Reverting an edit is deleting its row — the
    auto-collected data is never mutated, so no snapshot is kept.
    """
    id = AutoField()
    software_name    = CharField()
    resource_name    = CharField()
    software_version = CharField()
    # auto command this edit targets; NULL = admin-added command
    target_command   = TextField(null=True, default=None)
    # hide the targeted command from display
    suppressed       = BooleanField(default=False)
    # replacement display text; for admin-added rows, the command itself
    replacement      = TextField(null=True, default=None)
    # show this command first, overriding the canonical order
    is_primary       = BooleanField(default=False)
    edited_at        = TextField(null=True, default=None)
    edited_by        = TextField(null=True, default=None)

    class Meta:
        # One edit per targeted command; NULL targets (admin-added rows)
        # are distinct under SQLite, so a version can hold several.
        indexes = (
            (
                (
                    "software_name",
                    "resource_name",
                    "software_version",
                    "target_command",
                ),
                True,
            ),
        )
