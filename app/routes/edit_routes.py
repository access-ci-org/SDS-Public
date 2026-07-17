import datetime
import json
import re

from flask import abort, redirect, render_template, request, Response, url_for
from flask_login import current_user
from peewee import DoesNotExist

from app.logic.chain_projection import canonical_order, project_entry
from app.logic.overrides import revert_override, set_overrides
from app.models import db, persistent_db
from app.models.fields import AI_FIELD_NAMES, ALL_FIELDS, SOFTWARE_FIELD_MAP
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.command_edit import CommandEdit
from app.models.resource import Resource
from app.models.software import Software
from app.models.software_edit import SoftwareEdit
from app.models.softwareResource import SoftwareResource
from app.routes._decorators import admin_required
from . import edit_bp

# Command-tab form fields: block__{b}__resource / __version (hidden),
# block__{b}__chain__{i}__target / __text / __hide, block__{b}__added__{j},
# block__{b}__new, block__{b}__primary. Resource and version travel in
# VALUES, never in field names, so their content can't break parsing.
_BLOCK_FIELD_RE = re.compile(r"^block__(\d+)__(.+)$")
_CHAIN_TARGET_RE = re.compile(r"^chain__(\d+)__target$")
_ADDED_RE = re.compile(r"^added__(\d+)$")


def _now_stamp():
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")


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


def _build_fields(sw, ai, edit):
    fields = {}
    for edit_field, sw_field in SOFTWARE_FIELD_MAP.items():
        override = getattr(edit, edit_field, None) if edit else None
        fields[edit_field] = {
            "value": override if override is not None else (getattr(sw, sw_field, "") or ""),
            "is_overridden": override is not None,
        }
    for edit_field in AI_FIELD_NAMES:
        override = getattr(edit, edit_field, None) if edit else None
        fields[edit_field] = {
            "value": override if override is not None else ((getattr(ai, edit_field, "") or "") if ai else ""),
            "is_overridden": override is not None,
        }
    return fields


def _command_edit_key(software_name, resource_name, version):
    return (
        (CommandEdit.software_name == software_name)
        & (CommandEdit.resource_name == resource_name)
        & (CommandEdit.software_version == version)
    )


def _added_edits_in_order(edits):
    return sorted(
        (e for e in edits if e.target_command is None),
        key=lambda e: (e.edited_at or "", e.id),
    )


def _build_command_data(sw):
    """Per-entry chain data for the Resource Commands tab: each visible
    collected command with its edit state, the admin-added commands, and
    which one (if any) is pinned primary."""
    entries = (
        SoftwareResource
        .select(SoftwareResource, Resource)
        .join(Resource)
        .where(SoftwareResource.software_id == sw.id)
        .order_by(Resource.resource_name, SoftwareResource.software_version)
    )

    result = []
    for index, sr in enumerate(entries):
        resource_name = sr.resource_id.resource_name
        version = sr.software_version
        edits = list(CommandEdit.select().where(
            _command_edit_key(sw.software_name, resource_name, version)
        ))
        by_target = {
            e.target_command: e for e in edits if e.target_command is not None
        }

        chains = []
        primary_value = "auto"
        visible = canonical_order(
            [r for r in sr.load_commands if not r.admin_added and not r.hidden]
        )
        for i, row in enumerate(visible):
            e = by_target.get(row.command)
            replaced = bool(e and e.replacement is not None)
            if e and e.is_primary:
                primary_value = f"chain__{i}"
            chains.append({
                "target": row.command,
                "text": e.replacement if replaced else row.command,
                "is_replaced": replaced,
                "is_hidden": bool(e and e.suppressed),
            })

        added = []
        for j, e in enumerate(_added_edits_in_order(edits)):
            if e.is_primary:
                primary_value = f"added__{j}"
            added.append(e.replacement or "")

        result.append({
            "index": index,
            "resource_name": resource_name,
            "software_version": version,
            "chains": chains,
            "added": added,
            "primary_value": primary_value,
            "is_overridden": bool(edits),
        })

    return result


def _stale_command_edits(sw):
    """Edits that no longer match anything collected: the entry vanished,
    or the targeted command did. They have no display effect; the panel
    lists them for deletion."""
    collected = {}
    entries = (
        SoftwareResource
        .select(SoftwareResource, Resource)
        .join(Resource)
        .where(SoftwareResource.software_id == sw.id)
    )
    for sr in entries:
        key = (sr.resource_id.resource_name, sr.software_version)
        collected[key] = {
            r.command for r in sr.load_commands if not r.admin_added
        }

    stale = []
    for e in CommandEdit.select().where(
        CommandEdit.software_name == sw.software_name
    ):
        key = (e.resource_name, e.software_version)
        entry_gone = key not in collected
        target_gone = (
            e.target_command is not None
            and not entry_gone
            and e.target_command not in collected[key]
        )
        if not (entry_gone or target_gone):
            continue
        if e.target_command is None:
            what = f'added command "{e.replacement}"'
        elif e.replacement is not None:
            what = f'"{e.target_command}" replaced with "{e.replacement}"'
        elif e.suppressed:
            what = f'"{e.target_command}" hidden'
        else:
            what = f'"{e.target_command}" pinned primary'
        stale.append({
            "id": e.id,
            "resource_name": e.resource_name,
            "software_version": e.software_version,
            "description": what,
        })
    return stale


def _render_panel(name, sw, ai, edit):
    return render_template(
        "admin/edit_panel.html",
        software_name=name,
        fields=_build_fields(sw, ai, edit),
        command_data=_build_command_data(sw),
        stale_edits=_stale_command_edits(sw),
        edit=edit,
        core_fields=list(SOFTWARE_FIELD_MAP),
        ai_fields=AI_FIELD_NAMES,
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

    data = request.form
    now = _now_stamp()
    values = {f: data[f] for f in ALL_FIELDS if f in data}

    with db.atomic(), persistent_db.atomic():
        set_overrides(name, values, actor=current_user.username, timestamp=now)

        # Handle per-chain command edits, grouped by block__{b}__ fields.
        # Each block is one (resource, version): hide flags and text
        # replacements per collected command, added commands (blank =
        # removed), and the primary pick. The desired edit set is compared
        # against the stored one and replaced only when it differs, so an
        # untouched form leaves rows and audit stamps alone.
        blocks = {}
        for key, value in data.items():
            m = _BLOCK_FIELD_RE.match(key)
            if m:
                blocks.setdefault(int(m.group(1)), {})[m.group(2)] = value

        for fields_ in blocks.values():
            resource_name = fields_.get("resource")
            version = fields_.get("version")
            if not resource_name or version is None:
                continue

            try:
                resource = Resource.get(Resource.resource_name == resource_name)
                sr = SoftwareResource.get(
                    (SoftwareResource.software_id == sw.id) &
                    (SoftwareResource.resource_id == resource.id) &
                    (SoftwareResource.software_version == version)
                )
            except DoesNotExist:
                continue

            primary_sel = fields_.get("primary", "auto")

            chain_targets = {}
            for k, v in fields_.items():
                m = _CHAIN_TARGET_RE.match(k)
                if m:
                    chain_targets[int(m.group(1))] = v

            # ordered: chain edits, then added commands in form order —
            # creation order fixes the ids the projection sorts added
            # rows by
            desired = []
            targets = set(chain_targets.values())
            for i in sorted(chain_targets):
                target = chain_targets[i]
                text = (fields_.get(f"chain__{i}__text") or "").strip()
                suppressed = f"chain__{i}__hide" in fields_
                replacement = text if text and text != target else None
                is_primary = primary_sel == f"chain__{i}"
                if suppressed or replacement is not None or is_primary:
                    desired.append((target, suppressed, replacement, is_primary))

            added_fields = sorted(
                (int(m.group(1)), v)
                for k, v in fields_.items()
                if (m := _ADDED_RE.match(k))
            )
            seen_added = set()
            for j, value in added_fields:
                text = (value or "").strip()
                if not text or text in targets or text in seen_added:
                    continue
                seen_added.add(text)
                desired.append((None, False, text, primary_sel == f"added__{j}"))
            new_text = (fields_.get("new") or "").strip()
            if new_text and new_text not in targets and new_text not in seen_added:
                desired.append((None, False, new_text, False))

            key_filter = _command_edit_key(name, resource_name, version)
            existing = {
                (e.target_command, e.suppressed, e.replacement, e.is_primary)
                for e in CommandEdit.select().where(key_filter)
            }
            if set(desired) == existing:
                continue

            CommandEdit.delete().where(key_filter).execute()
            for target, suppressed, replacement, is_primary in desired:
                CommandEdit.create(
                    software_name=name,
                    resource_name=resource_name,
                    software_version=version,
                    target_command=target,
                    suppressed=suppressed,
                    replacement=replacement,
                    is_primary=is_primary,
                    edited_at=now,
                    edited_by=current_user.username,
                )

            project_entry(sr, list(CommandEdit.select().where(key_filter)))

    sw = _load_software(name)
    return _render_panel(name, sw, _load_ai(sw), _load_edit(name))


@edit_bp.route("/admin/edit/software/<path:name>/<field>", methods=["DELETE"])
@admin_required
def delete_field_override(name, field):
    if field not in ALL_FIELDS:
        abort(400)

    _load_software(name)
    revert_override(
        name, field, actor=current_user.username, timestamp=_now_stamp()
    )

    sw = _load_software(name)
    return _render_panel(name, sw, _load_ai(sw), _load_edit(name))


@edit_bp.route("/admin/edit/software/<path:name>/command/<resource_name>/<software_version>", methods=["DELETE"])
@admin_required
def delete_command_override(name, resource_name, software_version):
    """Revert an entry to its collected commands by deleting all of its
    edits and re-projecting — the collected rows were never mutated, so
    no snapshot is involved."""
    sw = _load_software(name)

    with db.atomic(), persistent_db.atomic():
        CommandEdit.delete().where(
            _command_edit_key(name, resource_name, software_version)
        ).execute()

        try:
            resource = Resource.get(Resource.resource_name == resource_name)
            sr = SoftwareResource.get(
                (SoftwareResource.software_id == sw.id) &
                (SoftwareResource.resource_id == resource.id) &
                (SoftwareResource.software_version == software_version)
            )
        except DoesNotExist:
            sr = None
        if sr is not None:
            project_entry(sr, [])

    return _render_panel(name, sw, _load_ai(sw), _load_edit(name))


@edit_bp.route("/admin/edit/software/<path:name>/command_edit/<int:edit_id>", methods=["DELETE"])
@admin_required
def delete_stale_command_edit(name, edit_id):
    """Delete one stale command edit by id. Stale edits have no display
    effect, so no re-projection is needed."""
    sw = _load_software(name)

    with persistent_db.atomic():
        CommandEdit.delete().where(
            (CommandEdit.id == edit_id)
            & (CommandEdit.software_name == name)
        ).execute()

    return _render_panel(name, sw, _load_ai(sw), _load_edit(name))


_PER_PAGE = 25


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
        n_overrides = sum(1 for f in ALL_FIELDS if edit and getattr(edit, f) is not None) if edit else 0
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
    sw_fields = ["software_name"] + list(ALL_FIELDS) + ["edited_at", "edited_by"]
    cmd_fields = [
        "software_name", "resource_name", "software_version",
        "target_command", "suppressed", "replacement", "is_primary",
        "edited_at", "edited_by",
    ]

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

    now = _now_stamp()
    valid_sw_fields = set(ALL_FIELDS)

    with db.atomic(), persistent_db.atomic():
        for record in data.get("software_edits", []):
            name = record.get("software_name")
            if not name:
                continue
            # Never accept snapshots from the import file — they're
            # local-to-this-instance and recaptured from the live values.
            fields = {k: v for k, v in record.items() if k in valid_sw_fields}
            if not fields:
                continue
            set_overrides(
                name, fields,
                actor=current_user.username, timestamp=now,
                skip_unchanged=False,
            )

        touched_keys = set()
        for record in data.get("command_edits", []):
            if "command" in record or "auto_command" in record:
                # whole-list export from before the per-chain model; the
                # shapes are not translatable, so the import is refused
                abort(400)
            sw_name = record.get("software_name")
            res_name = record.get("resource_name")
            version = record.get("software_version")
            if not (sw_name and res_name and version):
                continue

            target = record.get("target_command")
            suppressed = bool(record.get("suppressed"))
            replacement = record.get("replacement")
            is_primary = bool(record.get("is_primary"))
            if target is None and not (replacement or "").strip():
                continue

            if target is None:
                # admin-added command; keyed by its text since NULL
                # targets are distinct under the unique index
                edit = CommandEdit.get_or_none(
                    _command_edit_key(sw_name, res_name, version)
                    & CommandEdit.target_command.is_null()
                    & (CommandEdit.replacement == replacement)
                )
                if edit is None:
                    CommandEdit.create(
                        software_name=sw_name, resource_name=res_name,
                        software_version=version, replacement=replacement,
                        suppressed=suppressed, is_primary=is_primary,
                        edited_at=now, edited_by=current_user.username,
                    )
                else:
                    edit.suppressed = suppressed
                    edit.is_primary = is_primary
                    edit.edited_at = now
                    edit.edited_by = current_user.username
                    edit.save()
            else:
                CommandEdit.insert(
                    software_name=sw_name, resource_name=res_name,
                    software_version=version, target_command=target,
                    suppressed=suppressed, replacement=replacement,
                    is_primary=is_primary,
                    edited_at=now, edited_by=current_user.username,
                ).on_conflict(
                    conflict_target=[
                        CommandEdit.software_name,
                        CommandEdit.resource_name,
                        CommandEdit.software_version,
                        CommandEdit.target_command,
                    ],
                    update={
                        CommandEdit.suppressed: suppressed,
                        CommandEdit.replacement: replacement,
                        CommandEdit.is_primary: is_primary,
                        CommandEdit.edited_at: now,
                        CommandEdit.edited_by: current_user.username,
                    },
                ).execute()

            touched_keys.add((sw_name, res_name, version))

        for sw_name, res_name, version in touched_keys:
            try:
                sw = Software.get(Software.software_name == sw_name)
                resource = Resource.get(Resource.resource_name == res_name)
                sr = SoftwareResource.get(
                    (SoftwareResource.software_id == sw.id) &
                    (SoftwareResource.resource_id == resource.id) &
                    (SoftwareResource.software_version == version)
                )
            except DoesNotExist:
                continue
            project_entry(
                sr,
                list(CommandEdit.select().where(
                    _command_edit_key(sw_name, res_name, version)
                )),
            )

    return redirect(url_for("edit.admin_software_overview"))
