"""
Schema behavior of the per-chain CommandEdit model and the derived
display columns on SoftwareResourceCommand.
"""
import pytest
from peewee import IntegrityError

from app.models.command_edit import CommandEdit


def test_duplicate_target_edit_is_rejected(databases, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0", target_command="module load tool/1.0"
    )
    with pytest.raises(IntegrityError):
        CommandEdit.create(
            software_name="tool",
            resource_name="clusterx",
            software_version="1.0",
            target_command="module load tool/1.0",
        )


def test_same_target_allowed_across_versions(databases, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0", target_command="module load tool/1.0"
    )
    make_command_edit(
        "tool", "clusterx", "2.0", target_command="module load tool/1.0"
    )
    assert CommandEdit.select().count() == 2


def test_multiple_added_commands_per_entry_allowed(databases, make_command_edit):
    # NULL targets are distinct under the unique index, so one entry can
    # hold several admin-added commands
    make_command_edit("tool", "clusterx", "1.0", replacement="first added")
    make_command_edit("tool", "clusterx", "1.0", replacement="second added")
    assert CommandEdit.select().where(
        CommandEdit.target_command.is_null()
    ).count() == 2


def test_edit_defaults(databases, make_command_edit):
    edit = make_command_edit(
        "tool", "clusterx", "1.0", target_command="module load tool/1.0"
    )
    assert edit.suppressed is False
    assert edit.replacement is None
    assert edit.is_primary is False


def test_command_row_derived_column_defaults(
    databases, make_resource, make_software, make_software_resource,
    make_src_command
):
    resource = make_resource(name="clusterx")
    software = make_software(name="tool")
    sr = make_software_resource(software, resource, version="1.0", command="")
    row = make_src_command(sr, "module load tool/1.0")

    assert row.suppressed is False
    assert row.display_command is None
    assert row.display_rank is None
    assert row.admin_added is False
