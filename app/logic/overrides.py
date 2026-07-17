"""
Single home for projecting admin field overrides (SoftwareEdit in
sds_persistent.db) and example-use files onto the live display tables
(Software / AISoftwareInfo in sds_db.db). Per-chain command edits
(CommandEdit) are projected separately by app/logic/chain_projection.py.

Every code path that materializes field overrides goes through here: the
admin edit panel's save and revert routes, the overrides import, and the
end-of-rebuild projection in reset_database.py.

Override semantics per field:
- NULL   -> no override; the auto (pipeline) value shows
- ""     -> override that explicitly blanks the field
- value  -> override that replaces the field

The auto value of each overridden field is snapshotted
(SoftwareEdit.auto_values JSON) so revert can restore it. Request-time
operations capture the snapshot once, on first override; project_all()
re-captures from the freshly rebuilt rows so revert always restores the
current pipeline value.
"""
import json

from app.app_logging import logger
from app.models import db, ensure_snapshot_columns, persistent_db
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.banner import Banner
from app.models.fields import AI_FIELD_NAMES, ALL_FIELDS, SOFTWARE_FIELD_MAP
from app.models.software import Software
from app.models.software_edit import SoftwareEdit


def _load_auto_values(edit):
    """Snapshot dict from a SoftwareEdit row ({} when absent or corrupt)."""
    if not edit or not edit.auto_values:
        return {}
    try:
        return json.loads(edit.auto_values)
    except (json.JSONDecodeError, TypeError):
        return {}


def _store_auto_values(edit, mapping):
    edit.auto_values = json.dumps(mapping) if mapping else None


def set_overrides(name, values, *, actor, timestamp, skip_unchanged=True):
    """Set field overrides for one software and write them through to the
    live tables.

    values maps edit-field name -> new value. A value of None clears the
    stored override without touching the live tables (import records list
    every field explicitly, including un-overridden ones).

    skip_unchanged=True (interactive save): a field with no existing override
    whose value equals the auto value is ignored, so saving an untouched form
    creates no override rows. skip_unchanged=False (import/restore): every
    provided field becomes an override, even when identical to the auto value.

    The software may be absent from the catalog (an imported override for
    software this instance doesn't have): the override is stored with an
    empty-string snapshot and projected by project_all() once the software
    appears.
    """
    sw = Software.get_or_none(Software.software_name == name)
    ai = (
        AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id)
        if sw is not None
        else None
    )
    edit = SoftwareEdit.get_or_none(SoftwareEdit.software_name == name)

    is_new_edit = edit is None
    if is_new_edit:
        edit = SoftwareEdit(software_name=name)
    edit.edited_at = timestamp
    edit.edited_by = actor

    auto_values = _load_auto_values(edit)
    snapshots_changed = False
    sw_changed = False
    ai_changed = False
    ai_pending = {}  # AI field values to write when the ai row doesn't exist yet
    fields_set = False

    with db.atomic(), persistent_db.atomic():
        for field, new_val in values.items():
            if field not in ALL_FIELDS:
                continue
            if new_val is None:
                setattr(edit, field, None)
                fields_set = True
                continue

            existing_override = getattr(edit, field)
            if field in SOFTWARE_FIELD_MAP:
                sw_col = SOFTWARE_FIELD_MAP[field]
                auto_val = (getattr(sw, sw_col, "") or "") if sw else ""
            else:
                auto_val = (getattr(ai, field, "") or "") if ai else ""

            if skip_unchanged and existing_override is None and new_val == auto_val:
                continue

            if field not in auto_values:
                auto_values[field] = auto_val
                snapshots_changed = True
            setattr(edit, field, new_val)
            fields_set = True

            if sw is None:
                continue
            if field in SOFTWARE_FIELD_MAP:
                setattr(sw, SOFTWARE_FIELD_MAP[field], new_val)
                sw_changed = True
            elif ai is not None:
                setattr(ai, field, new_val)
                ai_changed = True
            else:
                ai_pending[field] = new_val

        if snapshots_changed:
            _store_auto_values(edit, auto_values)

        # A brand-new edit row is only persisted when it actually holds an
        # override; an existing row is always saved (updates edited_at/by).
        if not (is_new_edit and not fields_set):
            edit.save(force_insert=is_new_edit)
            if sw_changed:
                sw.save()
            if ai_changed:
                ai.save()
            if ai is None and ai_pending:
                AISoftwareInfo.create(software_id=sw.id, **ai_pending)

    return edit


def revert_override(name, field, *, actor, timestamp):
    """Remove one field override and restore the snapshotted auto value to
    the live table. The AISoftwareInfo row is created when the snapshot has
    to land somewhere and the row is missing.

    No-op when no edit row exists. A field overridden before its snapshot was
    captured (no auto_values entry) is cleared without touching the live
    value.
    """
    edit = SoftwareEdit.get_or_none(SoftwareEdit.software_name == name)
    if edit is None:
        return

    sw = Software.get_or_none(Software.software_name == name)
    ai = (
        AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id)
        if sw is not None
        else None
    )

    auto_values = _load_auto_values(edit)
    snapshot = auto_values.pop(field, None)

    with db.atomic(), persistent_db.atomic():
        if snapshot is not None and sw is not None:
            if field in SOFTWARE_FIELD_MAP:
                setattr(sw, SOFTWARE_FIELD_MAP[field], snapshot)
                sw.save()
            elif field in AI_FIELD_NAMES:
                if ai is not None:
                    setattr(ai, field, snapshot)
                    ai.save()
                else:
                    AISoftwareInfo.create(software_id=sw.id, **{field: snapshot})

        setattr(edit, field, None)
        _store_auto_values(edit, auto_values)
        edit.edited_at = timestamp
        edit.edited_by = actor
        edit.save()


def project_all():
    """Project every stored field override onto the freshly rebuilt live
    tables. Runs at the end of a database rebuild.

    Re-captures each overridden field's snapshot from the just-rebuilt row so
    revert restores the current pipeline value. Creates the AISoftwareInfo
    row when a software has AI overrides but the rebuild produced none.
    Overrides for software absent from the catalog stay dormant.
    """
    persistent_db.connect(reuse_if_open=True)
    persistent_db.create_tables([SoftwareEdit, Banner], safe=True)
    ensure_snapshot_columns(persistent_db)

    for edit in SoftwareEdit.select():
        sw = Software.get_or_none(Software.software_name == edit.software_name)
        if sw is None:
            continue

        snapshots = _load_auto_values(edit)
        snapshots_changed = False

        sw_changed = False
        for field, sw_col in SOFTWARE_FIELD_MAP.items():
            val = getattr(edit, field)
            if val is not None:
                snapshots[field] = getattr(sw, sw_col, "") or ""
                snapshots_changed = True
                setattr(sw, sw_col, val)
                sw_changed = True
        if sw_changed:
            sw.save()

        ai = AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id)
        if ai is not None:
            ai_changed = False
            for field in AI_FIELD_NAMES:
                val = getattr(edit, field)
                if val is not None:
                    snapshots[field] = getattr(ai, field, "") or ""
                    snapshots_changed = True
                    setattr(ai, field, val)
                    ai_changed = True
            if ai_changed:
                ai.save()
        else:
            # The rebuild produced no AISoftwareInfo row for this software;
            # create one from the AI overrides (the auto value is empty).
            ai_overrides = {
                field: getattr(edit, field)
                for field in AI_FIELD_NAMES
                if getattr(edit, field) is not None
            }
            if ai_overrides:
                for field in ai_overrides:
                    snapshots[field] = ""
                snapshots_changed = True
                AISoftwareInfo.create(software_id=sw.id, **ai_overrides)

        if snapshots_changed:
            _store_auto_values(edit, snapshots)
            edit.save()


def apply_example_use_files(directory):
    """Apply example-use files from the data directory to the live AI rows.

    Files are a pipeline data source, re-applied on every rebuild (before
    project_all): the file content becomes AISoftwareInfo.ai_example_use,
    and the row is created when missing. The software name is the file name
    with a .md suffix stripped when present; files are processed in sorted
    order, so when both forms exist the .md file wins. An empty file
    explicitly blanks the field.

    An admin override byte-identical to the file content is cleared as
    redundant — it duplicates the auto value, and clearing it keeps future
    file edits live. project_all() re-applies any remaining override on top.
    """
    if directory is None or not directory.is_dir():
        return

    for path in sorted(directory.iterdir()):
        if not path.is_file():
            logger.warning(
                f"Item {path} in the example-use directory is not a file. Skipping"
            )
            continue
        try:
            content = path.read_text(encoding="utf-8")
            name = path.name[: -len(".md")] if path.name.endswith(".md") else path.name

            sw = Software.get_or_none(Software.software_name == name)
            if sw is None:
                continue

            ai = AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id)
            if ai is None:
                AISoftwareInfo.create(software_id=sw.id, ai_example_use=content)
            else:
                ai.ai_example_use = content
                ai.save()

            edit = SoftwareEdit.get_or_none(SoftwareEdit.software_name == name)
            if edit is not None and edit.ai_example_use == content:
                auto_values = _load_auto_values(edit)
                auto_values.pop("ai_example_use", None)
                edit.ai_example_use = None
                _store_auto_values(edit, auto_values)
                edit.save()
        except Exception as e:
            logger.warning(f"Failed to apply example-use file {path}: {e}")
