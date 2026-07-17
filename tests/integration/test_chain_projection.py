"""
Chain-edit projection: CommandEdit rows resolve onto the derived
SoftwareResourceCommand columns (suppressed, display_command,
display_rank, admin_added) and SoftwareResource.command tracks the first
displayed text. Collected columns are never mutated; projection is
idempotent; edits without a matching target are inert.
"""
import pytest

from app.logic.chain_projection import project_all, project_entry
from app.models.command_edit import CommandEdit
from app.models.softwareResource import SoftwareResource
from app.models.softwareResourceCommand import SoftwareResourceCommand


@pytest.fixture
def entry(make_resource, make_software, make_software_resource, make_src_command):
    """One software/resource/version with three collected chains:
    a direct load, a one-parent chain, and a hidden one-parent chain."""
    resource = make_resource(name="clusterx")
    software = make_software(name="tool")
    sr = make_software_resource(
        software, resource, version="1.0", command="module load tool/1.0"
    )
    direct = make_src_command(sr, "module load tool/1.0", module_name="tool/1.0")
    chained = make_src_command(
        sr, "module load gcc/12.3.0 tool/1.0",
        module_name="tool/1.0", parent_chain="gcc/12.3.0",
    )
    hidden = make_src_command(
        sr, "module load intel/.2021.4.0 tool/1.0",
        module_name="tool/1.0", parent_chain="intel/.2021.4.0", hidden=True,
    )
    return {
        "resource": resource,
        "software": software,
        "sr": sr,
        "direct": direct,
        "chained": chained,
        "hidden": hidden,
    }


def _edits(software_name="tool", resource_name="clusterx", version="1.0"):
    return list(CommandEdit.select().where(
        (CommandEdit.software_name == software_name)
        & (CommandEdit.resource_name == resource_name)
        & (CommandEdit.software_version == version)
    ))


def _ranked_texts(sr):
    rows = sorted(
        (r for r in sr.load_commands if r.display_rank is not None),
        key=lambda r: r.display_rank,
    )
    return [
        r.display_command if r.display_command is not None else r.command
        for r in rows
    ]


def _reload(sr):
    return SoftwareResource.get(SoftwareResource.id == sr.id)


def test_no_edits_ranks_visible_chains_direct_load_first(entry):
    project_entry(entry["sr"], [])

    assert _ranked_texts(entry["sr"]) == [
        "module load tool/1.0",
        "module load gcc/12.3.0 tool/1.0",
    ]
    hidden = SoftwareResourceCommand.get(SoftwareResourceCommand.id == entry["hidden"].id)
    assert hidden.display_rank is None
    assert _reload(entry["sr"]).command == "module load tool/1.0"


def test_suppress_edit_hides_chain(entry, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0",
        target_command="module load tool/1.0", suppressed=True,
    )
    project_entry(entry["sr"], _edits())

    assert _ranked_texts(entry["sr"]) == ["module load gcc/12.3.0 tool/1.0"]
    assert _reload(entry["sr"]).command == "module load gcc/12.3.0 tool/1.0"


def test_replacement_edit_changes_display_text(entry, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0",
        target_command="module load tool/1.0",
        replacement="ml tool/1.0",
    )
    project_entry(entry["sr"], _edits())

    assert _ranked_texts(entry["sr"])[0] == "ml tool/1.0"
    assert _reload(entry["sr"]).command == "ml tool/1.0"
    # the collected text is untouched
    direct = SoftwareResourceCommand.get(SoftwareResourceCommand.id == entry["direct"].id)
    assert direct.command == "module load tool/1.0"


def test_added_command_appends(entry, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0", replacement="run-tool.sh",
    )
    project_entry(entry["sr"], _edits())

    texts = _ranked_texts(entry["sr"])
    assert texts[-1] == "run-tool.sh"
    added = SoftwareResourceCommand.get(SoftwareResourceCommand.command == "run-tool.sh")
    assert added.admin_added is True


def test_primary_edit_reorders(entry, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0",
        target_command="module load gcc/12.3.0 tool/1.0", is_primary=True,
    )
    project_entry(entry["sr"], _edits())

    assert _ranked_texts(entry["sr"])[0] == "module load gcc/12.3.0 tool/1.0"
    assert _reload(entry["sr"]).command == "module load gcc/12.3.0 tool/1.0"


def test_suppressing_everything_is_respected(entry, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0",
        target_command="module load tool/1.0", suppressed=True,
    )
    make_command_edit(
        "tool", "clusterx", "1.0",
        target_command="module load gcc/12.3.0 tool/1.0", suppressed=True,
    )
    project_entry(entry["sr"], _edits())

    assert _ranked_texts(entry["sr"]) == []
    assert _reload(entry["sr"]).command == ""


def test_hidden_only_entry_falls_back_to_best_hidden(
    make_resource, make_software, make_software_resource, make_src_command
):
    resource = make_resource(name="clusterx")
    software = make_software(name="ghost")
    sr = make_software_resource(software, resource, version="2.0", command="")
    make_src_command(
        sr, "module load intel/.2021.4.0 ghost/2.0",
        parent_chain="intel/.2021.4.0", hidden=True,
    )
    make_src_command(
        sr, "module load intel/.2021.4.0 impi/2021.4.0 ghost/2.0",
        parent_chain="intel/.2021.4.0 impi/2021.4.0", hidden=True,
    )

    project_entry(sr, [])

    assert _ranked_texts(sr) == ["module load intel/.2021.4.0 ghost/2.0"]
    assert SoftwareResource.get(SoftwareResource.id == sr.id).command == (
        "module load intel/.2021.4.0 ghost/2.0"
    )


def test_orphaned_edit_is_inert(entry, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0",
        target_command="module load gone/9.9 tool/1.0", suppressed=True,
    )
    project_entry(entry["sr"], _edits())

    assert _ranked_texts(entry["sr"]) == [
        "module load tool/1.0",
        "module load gcc/12.3.0 tool/1.0",
    ]


def test_projection_is_idempotent(entry, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0",
        target_command="module load tool/1.0", suppressed=True,
    )
    make_command_edit("tool", "clusterx", "1.0", replacement="run-tool.sh")

    project_entry(entry["sr"], _edits())
    first = _ranked_texts(entry["sr"])
    first_count = SoftwareResourceCommand.select().count()

    project_entry(entry["sr"], _edits())

    assert _ranked_texts(entry["sr"]) == first
    assert SoftwareResourceCommand.select().count() == first_count


def test_reverting_restores_collected_state(entry, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0",
        target_command="module load tool/1.0", suppressed=True,
    )
    make_command_edit("tool", "clusterx", "1.0", replacement="run-tool.sh")
    project_entry(entry["sr"], _edits())

    CommandEdit.delete().execute()
    project_entry(entry["sr"], [])

    assert _ranked_texts(entry["sr"]) == [
        "module load tool/1.0",
        "module load gcc/12.3.0 tool/1.0",
    ]
    assert _reload(entry["sr"]).command == "module load tool/1.0"
    assert SoftwareResourceCommand.select().where(
        SoftwareResourceCommand.admin_added == True  # noqa: E712
    ).count() == 0


def test_entry_without_collected_rows_or_edits_is_left_alone(
    make_resource, make_software, make_software_resource
):
    resource = make_resource(name="clusterx")
    software = make_software(name="csvpkg")
    sr = make_software_resource(software, resource, version="3.0", command="csv command")

    project_entry(sr, [])

    assert SoftwareResource.get(SoftwareResource.id == sr.id).command == "csv command"


def test_project_all_applies_edits_by_natural_key(entry, make_command_edit):
    make_command_edit(
        "tool", "clusterx", "1.0",
        target_command="module load tool/1.0", suppressed=True,
    )

    project_all()

    assert _reload(entry["sr"]).command == "module load gcc/12.3.0 tool/1.0"
