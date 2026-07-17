"""Materialize persistent per-chain command edits onto the transient
command rows.

CommandEdit rows (persistent DB) describe admin intent against the
auto-collected SoftwareResourceCommand rows (transient DB): suppress a
command, replace its text, add a custom command, or pick which one shows
first. Projection resolves that intent into the derived columns
(suppressed, display_command, display_rank, admin_added) and keeps
SoftwareResource.command equal to the first displayed text, so every
surface that reads the single canonical command stays override-aware.

Projection is idempotent: the collected columns are never mutated, and
admin-added rows are deleted and re-materialized from their edits each
pass. Edits whose target no longer matches any collected command are
inert here (the admin panel surfaces them as stale).
"""
import re
from collections import defaultdict

from app.models import db
from app.models.command_edit import CommandEdit
from app.models.resource import Resource
from app.models.software import Software
from app.models.softwareResource import SoftwareResource
from app.models.softwareResourceCommand import SoftwareResourceCommand


def chain_sort_key(parents: list[str]) -> tuple:
    """Natural-order key for a parent chain so 'gcc/11.2.0' ranks above
    'gcc/9.5.0'. Numeric runs compare as integers; each fragment is tagged
    so mixed int/str comparisons cannot occur. The spider ingest imports
    this for canonical selection so display order can't drift from it."""
    key = []
    for module in parents:
        for part in re.split(r"(\d+)", module):
            key.append((0, int(part)) if part.isdigit() else (1, part))
    return tuple(key)


def canonical_order(rows):
    """Order command rows by the canonical rule: fewest parents first
    (zero = directly loadable), newest parents as tiebreak."""
    rows = sorted(
        rows,
        key=lambda r: chain_sort_key(r.parent_chain.split()),
        reverse=True,
    )
    return sorted(rows, key=lambda r: len(r.parent_chain.split()))


def display_text(row):
    return row.display_command if row.display_command is not None else row.command


def _auto_rows(rows):
    """The command rows an entry displays with zero edits, in canonical
    order: the visible collected commands, or the best hidden one when
    the entry has nothing visible."""
    rows = [r for r in rows if not r.admin_added]
    visible = canonical_order([r for r in rows if not r.hidden])
    if visible:
        return visible
    return canonical_order([r for r in rows if r.hidden])[:1]


def resolved_texts_from_rows(rows, fallback_command, has_edits):
    """The command texts an entry displays, from pre-fetched command rows
    (callers listing many entries batch one query and group by entry).
    fallback_command covers entries with no collected rows (e.g. CSV)."""
    ranked = sorted(
        (r for r in rows if r.display_rank is not None),
        key=lambda r: r.display_rank,
    )
    if ranked or has_edits:
        # projection output is authoritative; empty means the admin
        # suppressed everything
        return [display_text(r) for r in ranked]
    texts = [r.command for r in _auto_rows(rows)]
    if texts:
        return texts
    return [fallback_command] if fallback_command else []


def resolved_command_texts(sr, has_edits):
    """The command texts an entry currently displays, in display order."""
    return resolved_texts_from_rows(list(sr.load_commands), sr.command, has_edits)


def _matches(edit, row):
    if edit.target_command is not None:
        return not row.admin_added and row.command == edit.target_command
    return row.admin_added and row.command == (edit.replacement or "").strip()


def project_entry(sr, edits):
    """Project the given CommandEdit rows onto one SoftwareResource entry.

    A SoftwareResource without any collected command rows and without
    edits is left alone — its command came from a source that doesn't
    collect chains (e.g. CSV), and there is nothing to resolve.
    """
    rows = list(sr.load_commands)
    if not rows and not edits:
        return

    auto_rows = [r for r in rows if not r.admin_added]
    for r in rows:
        if r.admin_added:
            r.delete_instance()

    by_target = {}
    added_edits = []
    for e in edits:
        if e.target_command is None:
            added_edits.append(e)
        else:
            by_target[e.target_command] = e

    for r in auto_rows:
        e = by_target.get(r.command)
        r.suppressed = bool(e and e.suppressed)
        r.display_command = e.replacement if e else None

    visible = [r for r in auto_rows if not r.hidden]
    candidates = [r for r in visible if not r.suppressed]

    if candidates:
        ordered = canonical_order(candidates)
    elif visible:
        # the admin suppressed every visible command: respect it
        ordered = []
    else:
        # hidden-only entry: fall back to the best hidden command
        hidden_rows = canonical_order([r for r in auto_rows if r.hidden])
        ordered = hidden_rows[:1]

    added_rows = []
    for e in sorted(added_edits, key=lambda e: (e.edited_at or "", e.id)):
        text = (e.replacement or "").strip()
        if not text:
            continue
        row, created = SoftwareResourceCommand.get_or_create(
            software_resource_id=sr,
            command=text,
            defaults={"hidden": False, "admin_added": True},
        )
        # an added text identical to a collected command is already
        # represented by the auto row; drop the duplicate materialization
        if created:
            added_rows.append(row)

    display_list = ordered + added_rows

    primary_row = next(
        (
            r
            for e in edits
            if e.is_primary
            for r in display_list
            if _matches(e, r)
        ),
        None,
    )
    if primary_row is not None:
        display_list = [primary_row] + [r for r in display_list if r is not primary_row]

    for rank, r in enumerate(display_list):
        r.display_rank = rank
    for r in auto_rows:
        if r not in display_list:
            r.display_rank = None
    for r in auto_rows + added_rows:
        r.save()

    new_command = display_text(display_list[0]) if display_list else ""
    if sr.command != new_command:
        sr.command = new_command
        sr.save()


def _edits_by_key():
    grouped = defaultdict(list)
    for e in CommandEdit.select():
        grouped[(e.software_name, e.resource_name, e.software_version)].append(e)
    return grouped


def project_all():
    """Project every entry; called after a data rebuild."""
    grouped = _edits_by_key()
    entries = (
        SoftwareResource
        .select(SoftwareResource, Software, Resource)
        .join(Software)
        .switch(SoftwareResource)
        .join(Resource)
    )
    with db.atomic():
        for sr in entries:
            key = (
                sr.software_id.software_name,
                sr.resource_id.resource_name,
                sr.software_version,
            )
            project_entry(sr, grouped.get(key, []))


def project_software(sw):
    """Project every entry of one Software row; called after admin saves."""
    grouped = _edits_by_key()
    entries = (
        SoftwareResource
        .select(SoftwareResource, Resource)
        .join(Resource)
        .where(SoftwareResource.software_id == sw.id)
    )
    with db.atomic():
        for sr in entries:
            key = (
                sw.software_name,
                sr.resource_id.resource_name,
                sr.software_version,
            )
            project_entry(sr, grouped.get(key, []))
