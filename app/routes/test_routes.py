"""
Test-only seed endpoint for end-to-end tests.

Gated by the TESTING=1 environment variable. Without it the routes return 404,
so the endpoint is inert in production even if the blueprint is registered.

The seed endpoint:
- Ensures all required tables exist in both databases
- Truncates every table
- Inserts rows from the JSON payload
- Resets the in-memory TABLE_INFO singleton
"""
import os

from flask import abort, jsonify, request

from app.models import db, persistent_db
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.command_edit import CommandEdit
from app.models.containers import Container
from app.models.resource import Resource
from app.models.software import Software
from app.models.softwareContainer import SoftwareContainer
from app.models.softwareResource import SoftwareResource
from app.models.banner import Banner
from app.models.software_edit import SoftwareEdit
from app.models.users import Users

from . import test_bp


TRANSIENT_MODELS = [
    Resource,
    Software,
    SoftwareResource,
    AISoftwareInfo,
    Container,
    SoftwareContainer,
    Users,
]

PERSISTENT_MODELS = [SoftwareEdit, CommandEdit, Banner]

# FK-safe delete order: children before parents
DELETE_ORDER = [
    SoftwareContainer,
    SoftwareResource,
    CommandEdit,
    SoftwareEdit,
    Banner,
    Container,
    AISoftwareInfo,
    Software,
    Resource,
    Users,
]


def _testing_enabled():
    return os.environ.get("TESTING") == "1"


@test_bp.route("/__test__/ping")
def test_ping():
    if not _testing_enabled():
        abort(404)
    return jsonify({"testing": True})


@test_bp.route("/__test__/seed", methods=["POST"])
def test_seed():
    if not _testing_enabled():
        abort(404)

    payload = request.get_json(silent=True) or {}

    db.connect(reuse_if_open=True)
    persistent_db.connect(reuse_if_open=True)
    db.create_tables(TRANSIENT_MODELS, safe=True)
    persistent_db.create_tables(PERSISTENT_MODELS, safe=True)

    for model in DELETE_ORDER:
        try:
            model.delete().execute()
        except Exception:
            pass

    # The TABLE_INFO singleton caches column metadata; clear it so the next
    # request rebuilds from current config.
    from app.logic import table as table_module
    table_module.TABLE_INFO = None

    resource_lookup = {}
    for name in payload.get("resources", []):
        resource_lookup[name] = Resource.create(resource_name=name)

    software_lookup = {}
    for sw in payload.get("software", []):
        soft = Software.create(
            software_name=sw["name"],
            software_description=sw.get("description", ""),
            software_web_page=sw.get("web_page", ""),
            software_documentation=sw.get("documentation", ""),
            software_use_link=sw.get("use_link", ""),
        )
        software_lookup[sw["name"]] = soft

        for sr in sw.get("resources", []):
            res = resource_lookup.get(sr["resource"])
            if res is None:
                res = Resource.create(resource_name=sr["resource"])
                resource_lookup[sr["resource"]] = res
            SoftwareResource.create(
                software_id=soft,
                resource_id=res,
                software_version=sr.get("version", ""),
                command=sr.get("command", ""),
            )

        ai_data = sw.get("ai")
        if ai_data:
            AISoftwareInfo.create(software_id=soft, **ai_data)

    for u in payload.get("users", []):
        Users.create(
            username=u["username"],
            password=Users.hash_password(u["password"]),
            is_admin=u.get("is_admin", False),
            email=u.get("email") or f"{u['username']}@test.local",
        )

    for c in payload.get("containers", []):
        res = resource_lookup.get(c["resource"])
        if res is None:
            res = Resource.create(resource_name=c["resource"])
            resource_lookup[c["resource"]] = res
        cont = Container.create(
            container_name=c["name"],
            resource_id=res,
            definition_file=c.get("definition_file", ""),
            container_file=c.get("container_file", ""),
            notes=c.get("notes", ""),
        )
        for sc in c.get("software", []):
            soft = software_lookup.get(sc["software"])
            if soft is None:
                continue
            SoftwareContainer.create(
                software_id=soft,
                container_id=cont,
                software_versions=sc.get("versions", ""),
                command=sc.get("command", ""),
            )

    for se in payload.get("software_edits", []):
        SoftwareEdit.create(**se)

    for ce in payload.get("command_edits", []):
        CommandEdit.create(**ce)

    for b in payload.get("banners", []):
        Banner.create(
            message=b["message"],
            severity=b.get("severity", "info"),
            pages=b.get("pages", "all-user-facing"),
            is_active=b.get("is_active", True),
            dismissible=b.get("dismissible", True),
            created_at=b.get("created_at", "2026-01-01T00:00:00"),
            created_by=b.get("created_by", "admin1"),
        )

    return jsonify({"ok": True})
