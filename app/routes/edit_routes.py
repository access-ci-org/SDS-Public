import datetime
import json

from flask import abort, redirect, render_template, request, Response, url_for
from flask_login import current_user
from peewee import DoesNotExist

from app.models import db, persistent_db
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.command_edit import CommandEdit
from app.models.resource import Resource
from app.models.software import Software
from app.models.software_edit import SoftwareEdit
from app.models.softwareResource import SoftwareResource
from app.routes._decorators import admin_required
from . import edit_bp

SOFTWARE_FIELDS = {
    "description": "software_description",
    "web_page": "software_web_page",
    "documentation": "software_documentation",
    "use_link": "software_use_link",
}

AI_FIELDS = [
    "ai_description",
    "ai_software_type",
    "ai_software_class",
    "ai_research_field",
    "ai_research_area",
    "ai_research_discipline",
    "ai_core_features",
    "ai_general_tags",
    "ai_example_use",
]

ALL_EDIT_FIELDS = list(SOFTWARE_FIELDS.keys()) + AI_FIELDS

CMD_PREFIX = "cmd__"


def _load_software(name):
    try:
        return Software.get(Software.software_name == name)
    except DoesNotExist:
        abort(404)


def _load_ai(sw):
    try:
        return AISoftwareInfo.get(AISoftwareInfo.software_id == sw.id)
    except DoesNotExist:
        return None


def _load_edit(name):
    try:
        return SoftwareEdit.get(SoftwareEdit.software_name == name)
    except DoesNotExist:
        return None


def _load_auto_values(edit):
    if not edit or not edit.auto_values:
        return {}
    try:
        return json.loads(edit.auto_values)
    except (json.JSONDecodeError, TypeError):
        return {}


def _store_auto_values(edit, mapping):
    edit.auto_values = json.dumps(mapping) if mapping else None


def _build_fields(sw, ai, edit):
    fields = {}
    for edit_field, sw_field in SOFTWARE_FIELDS.items():
        override = getattr(edit, edit_field, None) if edit else None
        fields[edit_field] = {
            "value": override if override is not None else (getattr(sw, sw_field, "") or ""),
            "is_overridden": override is not None,
        }
    for edit_field in AI_FIELDS:
        override = getattr(edit, edit_field, None) if edit else None
        fields[edit_field] = {
            "value": override if override is not None else ((getattr(ai, edit_field, "") or "") if ai else ""),
            "is_overridden": override is not None,
        }
    return fields


def _commands_to_display(command_str):
    """Convert comma-separated storage format to newline-separated display format."""
    if not command_str:
        return ""
    return "\n".join(c.strip() for c in command_str.split(",") if c.strip())


def _display_to_commands(textarea_val):
    """Convert newline-separated textarea input to comma-separated storage format."""
    if not textarea_val:
        return ""
    return ", ".join(c.strip() for c in textarea_val.splitlines() if c.strip())


def _build_command_data(sw):
    """Build resource/version/command data for the Resources tab."""
    rows = (
        SoftwareResource
        .select(SoftwareResource, Resource)
        .join(Resource)
        .where(SoftwareResource.software_id == sw.id)
        .order_by(Resource.resource_name, SoftwareResource.software_version)
    )

    result = []
    for sr in rows:
        resource_name = sr.resource_id.resource_name
        version = sr.software_version
        try:
            cmd_edit = CommandEdit.get(
                (CommandEdit.software_name == sw.software_name) &
                (CommandEdit.resource_name == resource_name) &
                (CommandEdit.software_version == version)
            )
            is_overridden = cmd_edit.command is not None
            display_val = _commands_to_display(cmd_edit.command if is_overridden else sr.command)
        except CommandEdit.DoesNotExist:
            is_overridden = False
            display_val = _commands_to_display(sr.command)

        result.append({
            "resource_name": resource_name,
            "software_version": version,
            "display_value": display_val,
            "is_overridden": is_overridden,
        })

    return result


def _render_panel(name, sw, ai, edit):
    return render_template(
        "admin/edit_panel.html",
        software_name=name,
        fields=_build_fields(sw, ai, edit),
        command_data=_build_command_data(sw),
        edit=edit,
    )


@edit_bp.route("/admin/edit/software/<path:name>")
@admin_required
def get_software_edit(name):
    sw = _load_software(name)
    return _render_panel(name, sw, _load_ai(sw), _load_edit(name))


@edit_bp.route("/admin/edit/software/<path:name>", methods=["PUT"])
@admin_required
def put_software_edit(name):
    sw = _load_software(name)
    ai = _load_ai(sw)
    edit = _load_edit(name)

    data = request.form
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")

    is_new_edit = edit is None
    if is_new_edit:
        edit = SoftwareEdit(software_name=name)

    edit.edited_at = now
    edit.edited_by = current_user.username

    sw_changed = False
    ai_changed = False
    ai_pending = {}  # AI field values to write when ai row doesn't exist yet
    auto_values = _load_auto_values(edit)
    auto_values_changed = False

    for edit_field, sw_field in SOFTWARE_FIELDS.items():
        if edit_field not in data:
            continue
        new_val = data[edit_field]
        existing_override = getattr(edit, edit_field)
        auto_val = getattr(sw, sw_field, "") or ""
        if existing_override is not None or new_val != auto_val:
            if edit_field not in auto_values:
                auto_values[edit_field] = auto_val
                auto_values_changed = True
            setattr(edit, edit_field, new_val)
            setattr(sw, sw_field, new_val)
            sw_changed = True

    for edit_field in AI_FIELDS:
        if edit_field not in data:
            continue
        new_val = data[edit_field]
        existing_override = getattr(edit, edit_field)
        auto_val = (getattr(ai, edit_field, "") or "") if ai else ""
        if existing_override is not None or new_val != auto_val:
            if edit_field not in auto_values:
                auto_values[edit_field] = auto_val
                auto_values_changed = True
            setattr(edit, edit_field, new_val)
            if ai:
                setattr(ai, edit_field, new_val)
                ai_changed = True
            else:
                ai_pending[edit_field] = new_val

    if auto_values_changed:
        _store_auto_values(edit, auto_values)

    any_changed = sw_changed or ai_changed or bool(ai_pending)

    with db.atomic(), persistent_db.atomic():
        if not (is_new_edit and not any_changed):
            edit.save(force_insert=is_new_edit)
            if sw_changed:
                sw.save()
            if ai_changed:
                ai.save()
            if ai is None and ai_pending:
                ai = AISoftwareInfo.create(software_id=sw.id, **ai_pending)

        # Handle command overrides — keyed cmd__{resource}__{version}
        for key, textarea_val in data.items():
            if not key.startswith(CMD_PREFIX):
                continue
            rest = key[len(CMD_PREFIX):]
            # split on first __ only so version can theoretically contain __
            parts = rest.split("__", 1)
            if len(parts) != 2:
                continue
            resource_name, version = parts

            new_command = _display_to_commands(textarea_val)

            # Look up current SoftwareResource command to compare
            try:
                resource = Resource.get(Resource.resource_name == resource_name)
                sr = SoftwareResource.get(
                    (SoftwareResource.software_id == sw.id) &
                    (SoftwareResource.resource_id == resource.id) &
                    (SoftwareResource.software_version == version)
                )
            except DoesNotExist:
                continue

            # Check existing override
            try:
                existing = CommandEdit.get(
                    (CommandEdit.software_name == name) &
                    (CommandEdit.resource_name == resource_name) &
                    (CommandEdit.software_version == version)
                )
                existing_override = existing.command
                existing_snapshot = existing.auto_command
            except CommandEdit.DoesNotExist:
                existing_override = None
                existing_snapshot = None

            auto_val = sr.command or ""
            if existing_override is None and new_command == auto_val:
                continue  # no change from auto, don't create a row

            # Capture snapshot on first override only
            snapshot_value = (
                existing_snapshot if existing_snapshot is not None else auto_val
            )

            # Upsert CommandEdit
            CommandEdit.insert(
                software_name=name,
                resource_name=resource_name,
                software_version=version,
                command=new_command,
                auto_command=snapshot_value,
                edited_at=now,
                edited_by=current_user.username,
            ).on_conflict(
                conflict_target=[
                    CommandEdit.software_name,
                    CommandEdit.resource_name,
                    CommandEdit.software_version,
                ],
                update={
                    CommandEdit.command: new_command,
                    CommandEdit.edited_at: now,
                    CommandEdit.edited_by: current_user.username,
                },
            ).execute()

            # Write through to sds_db immediately
            sr.command = new_command
            sr.save()

    return _render_panel(name, sw, ai, _load_edit(name))


@edit_bp.route("/admin/edit/software/<path:name>/<field>", methods=["DELETE"])
@admin_required
def delete_field_override(name, field):
    if field not in ALL_EDIT_FIELDS:
        abort(400)

    sw = _load_software(name)
    ai = _load_ai(sw)
    edit = _load_edit(name)

    if edit is not None:
        auto_values = _load_auto_values(edit)
        snapshot = auto_values.pop(field, None)

        with db.atomic(), persistent_db.atomic():
            if snapshot is not None:
                if field in SOFTWARE_FIELDS:
                    setattr(sw, SOFTWARE_FIELDS[field], snapshot)
                    sw.save()
                elif field in AI_FIELDS and ai is not None:
                    setattr(ai, field, snapshot)
                    ai.save()

            setattr(edit, field, None)
            _store_auto_values(edit, auto_values)
            edit.edited_at = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")
            edit.edited_by = current_user.username
            edit.save()

    return _render_panel(name, sw, ai, _load_edit(name))


@edit_bp.route("/admin/edit/software/<path:name>/command/<resource_name>/<software_version>", methods=["DELETE"])
@admin_required
def delete_command_override(name, resource_name, software_version):
    sw = _load_software(name)

    try:
        cmd_edit = CommandEdit.get(
            (CommandEdit.software_name == name) &
            (CommandEdit.resource_name == resource_name) &
            (CommandEdit.software_version == software_version)
        )
    except CommandEdit.DoesNotExist:
        cmd_edit = None

    with db.atomic(), persistent_db.atomic():
        if cmd_edit is not None and cmd_edit.auto_command is not None:
            try:
                resource = Resource.get(Resource.resource_name == resource_name)
                sr = SoftwareResource.get(
                    (SoftwareResource.software_id == sw.id) &
                    (SoftwareResource.resource_id == resource.id) &
                    (SoftwareResource.software_version == software_version)
                )
                sr.command = cmd_edit.auto_command
                sr.save()
            except DoesNotExist:
                pass

        CommandEdit.delete().where(
            (CommandEdit.software_name == name) &
            (CommandEdit.resource_name == resource_name) &
            (CommandEdit.software_version == software_version)
        ).execute()

    return _render_panel(name, sw, _load_ai(sw), _load_edit(name))


_PER_PAGE = 25
_ALL_OVERRIDE_FIELDS = list(SOFTWARE_FIELDS.keys()) + AI_FIELDS


@edit_bp.route("/admin/software")
@admin_required
def admin_software_overview():
    try:
        page = max(1, int(request.args.get("page", 1) or 1))
    except (TypeError, ValueError):
        page = 1
    search = request.args.get("search", "").strip()
    filter_mode = request.args.get("filter", "all")  # all | overrides | no_overrides

    edits_by_name = {e.software_name: e for e in SoftwareEdit.select()}
    override_names = set(edits_by_name.keys())

    total_count = Software.select().count()
    override_count = len(override_names)

    query = Software.select().order_by(Software.software_name)
    if search:
        query = query.where(Software.software_name.contains(search))
    if filter_mode == "overrides":
        if override_names:
            query = query.where(Software.software_name << list(override_names))
        else:
            query = query.where(Software.id == -1)
    elif filter_mode == "no_overrides" and override_names:
        query = query.where(Software.software_name.not_in(list(override_names)))

    total_filtered = query.count()
    total_pages = max(1, (total_filtered + _PER_PAGE - 1) // _PER_PAGE)
    page = min(page, total_pages)

    rows = []
    for sw in query.paginate(page, _PER_PAGE):
        edit = edits_by_name.get(sw.software_name)
        n_overrides = sum(1 for f in _ALL_OVERRIDE_FIELDS if edit and getattr(edit, f) is not None) if edit else 0
        rows.append({
            "name": sw.software_name,
            "description": sw.software_description or "",
            "has_edit": edit is not None,
            "n_overrides": n_overrides,
            "edited_by": edit.edited_by if edit else None,
            "edited_at": edit.edited_at[:10] if edit and edit.edited_at else None,
        })

    recently_edited = sorted(
        [e for e in SoftwareEdit.select() if e.edited_at],
        key=lambda e: e.edited_at,
        reverse=True,
    )[:10]

    return render_template(
        "admin/software_overview.html",
        rows=rows,
        total_count=total_count,
        override_count=override_count,
        not_edited_count=total_count - override_count,
        total_filtered=total_filtered,
        page=page,
        per_page=_PER_PAGE,
        total_pages=total_pages,
        search=search,
        filter_mode=filter_mode,
        recently_edited=recently_edited,
    )


@edit_bp.route("/admin/software/export")
@admin_required
def export_overrides():
    sw_fields = ["software_name"] + _ALL_OVERRIDE_FIELDS + ["edited_at", "edited_by"]
    cmd_fields = ["software_name", "resource_name", "software_version", "command", "edited_at", "edited_by"]

    payload = json.dumps({
        "software_edits": [{f: getattr(e, f) for f in sw_fields} for e in SoftwareEdit.select()],
        "command_edits": [{f: getattr(e, f) for f in cmd_fields} for e in CommandEdit.select()],
    }, indent=2, default=str)

    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=sds_overrides.json"},
    )


@edit_bp.route("/admin/software/import", methods=["POST"])
@admin_required
def import_overrides():
    f = request.files.get("overrides_file")
    if not f:
        abort(400)
    try:
        data = json.load(f)
    except Exception:
        abort(400)

    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")
    valid_sw_fields = set(_ALL_OVERRIDE_FIELDS)

    with db.atomic(), persistent_db.atomic():
        for record in data.get("software_edits", []):
            name = record.get("software_name")
            if not name:
                continue
            # Never accept snapshots from the import file — they're
            # local-to-this-instance and recaptured below.
            fields = {k: v for k, v in record.items() if k in valid_sw_fields}
            if not fields:
                continue

            sw = Software.get_or_none(Software.software_name == name)
            ai = AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == sw.id) if sw else None

            # Snapshot current sds_db values for every overridden field before
            # we stomp them. Merges with any existing auto_values on the row.
            existing_edit = SoftwareEdit.get_or_none(SoftwareEdit.software_name == name)
            auto_values = _load_auto_values(existing_edit)
            for edit_field, sw_field in SOFTWARE_FIELDS.items():
                if fields.get(edit_field) is not None and edit_field not in auto_values:
                    auto_values[edit_field] = (getattr(sw, sw_field, "") or "") if sw else ""
            for edit_field in AI_FIELDS:
                if fields.get(edit_field) is not None and edit_field not in auto_values:
                    auto_values[edit_field] = (getattr(ai, edit_field, "") or "") if ai else ""

            if existing_edit is not None:
                for k, v in fields.items():
                    setattr(existing_edit, k, v)
                existing_edit.auto_values = json.dumps(auto_values) if auto_values else None
                existing_edit.edited_at = now
                existing_edit.edited_by = current_user.username
                existing_edit.save()
            else:
                SoftwareEdit.create(
                    software_name=name,
                    auto_values=json.dumps(auto_values) if auto_values else None,
                    edited_at=now,
                    edited_by=current_user.username,
                    **fields,
                )

            if sw is None:
                continue

            sw_changed = False
            for edit_field, sw_field in SOFTWARE_FIELDS.items():
                if fields.get(edit_field) is not None:
                    setattr(sw, sw_field, fields[edit_field])
                    sw_changed = True
            if sw_changed:
                sw.save()

            ai_updates = {f: fields[f] for f in AI_FIELDS if fields.get(f) is not None}
            if ai_updates:
                if ai is not None:
                    for k, v in ai_updates.items():
                        setattr(ai, k, v)
                    ai.save()
                else:
                    AISoftwareInfo.create(software_id=sw.id, **ai_updates)

        for record in data.get("command_edits", []):
            sw_name = record.get("software_name")
            res_name = record.get("resource_name")
            version = record.get("software_version")
            command = record.get("command")
            if not (sw_name and res_name and version):
                continue

            # Capture local snapshot from current SoftwareResource, not from
            # the import file.
            snapshot = None
            sr = None
            if command is not None:
                try:
                    sw = Software.get(Software.software_name == sw_name)
                    resource = Resource.get(Resource.resource_name == res_name)
                    sr = SoftwareResource.get(
                        (SoftwareResource.software_id == sw.id) &
                        (SoftwareResource.resource_id == resource.id) &
                        (SoftwareResource.software_version == version)
                    )
                except DoesNotExist:
                    sr = None
                if sr is not None:
                    existing = CommandEdit.get_or_none(
                        (CommandEdit.software_name == sw_name) &
                        (CommandEdit.resource_name == res_name) &
                        (CommandEdit.software_version == version)
                    )
                    if existing is not None and existing.auto_command is not None:
                        snapshot = existing.auto_command
                    else:
                        snapshot = sr.command or ""

            CommandEdit.insert(
                software_name=sw_name, resource_name=res_name, software_version=version,
                command=command, auto_command=snapshot,
                edited_at=now, edited_by=current_user.username,
            ).on_conflict(
                conflict_target=[CommandEdit.software_name, CommandEdit.resource_name, CommandEdit.software_version],
                update={
                    CommandEdit.command: command,
                    CommandEdit.auto_command: snapshot,
                    CommandEdit.edited_at: now,
                    CommandEdit.edited_by: current_user.username,
                },
            ).execute()

            if command is not None and sr is not None:
                sr.command = command
                sr.save()

    return redirect(url_for("edit.admin_software_overview"))
