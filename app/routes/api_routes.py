import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from functools import wraps

from flask import jsonify, request, current_app
from werkzeug.exceptions import HTTPException
from app.app_logging import api_request_logger
from app.logic.chain_projection import resolved_texts_from_rows
from app.models.command_edit import CommandEdit
from app.models.software import Software
from app.models.resource import Resource
from app.models.softwareResource import SoftwareResource
from app.models.softwareResourceCommand import SoftwareResourceCommand
from app.models.softwareContainer import SoftwareContainer
from app.models.containers import Container
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.api_key import APIKey
from app.models.api_key_log import APIKeyLog
from . import api_bp

# Work caps: keys are admin-issued but there is no rate limiting, so these
# bound the cost of a single request instead.
SEARCH_RESULT_LIMIT = 100
MATCH_PACKAGES_LIMIT = 500

_SCHEMA = {
    "version": "1",
    "base_url": "/api/v1",
    "auth": {
        "type": "api_key",
        "header": "X-API-Key",
        "note": "All endpoints except /schema require a valid API key in the X-API-Key header.",
    },
    "endpoints": [
        {
            "path": "/schema",
            "method": "GET",
            "auth_required": False,
            "description": "Returns this schema document.",
            "response": {"type": "object"},
        },
        {
            "path": "/resources",
            "method": "GET",
            "auth_required": True,
            "description": "List all HPC clusters/resources tracked by this SDS instance.",
            "response": {
                "type": "array",
                "items": {"name": "string"},
            },
        },
        {
            "path": "/software/search",
            "method": "GET",
            "auth_required": True,
            "description": (
                "Search software by name, description, research field, or tags. "
                "Pass ?q=<query> to filter. At most 100 results are returned "
                "either way."
            ),
            "params": {"q": "string (optional)"},
            "response": {
                "type": "array",
                "items": {
                    "name": "string",
                    "description": "string",
                    "research_field": "string",
                    "software_type": "string",
                    "tags": "string",
                    "web_page": "string",
                    "documentation": "string",
                    "resources": "array of {resource: string, versions: [{version: string, command?: string, load_commands?: [string]}]}",
                    "has_containers": "boolean",
                },
            },
        },
        {
            "path": "/software/match-resources",
            "method": "POST",
            "auth_required": True,
            "description": (
                "Given a list of package names, return matching catalog entries "
                "and which resources support them. Unmatched packages listed separately."
            ),
            "body": {
                "packages": "array of strings (required, max 500)",
                "fuzzy": "boolean (default true)",
            },
            "response": {
                "matched": "array of {package: string, matches: [{software_name: string, score: number, description: string, resources: [string]}]}",
                "unmatched": "array of strings",
            },
        },
        {
            "path": "/software/{name}",
            "method": "GET",
            "auth_required": True,
            "description": "Full details for a software package including load commands and containers.",
            "response": {
                "name": "string",
                "description": "string",
                "research_field": "string",
                "software_type": "string",
                "tags": "string",
                "web_page": "string",
                "documentation": "string",
                "resources": "array of {resource: string, versions: [{version: string, command?: string, load_commands?: [string]}]}",
                "has_containers": "boolean",
                "containers": "array of {container_name: string, container_file: string, resource: string, versions: string, command: string, notes: string}",
            },
        },
        {
            "path": "/software/{name}/containers",
            "method": "GET",
            "auth_required": True,
            "description": "List container images available for a software package.",
            "response": {
                "type": "array",
                "items": {
                    "container_name": "string",
                    "container_file": "string",
                    "resource": "string",
                    "versions": "string",
                    "command": "string",
                    "notes": "string",
                },
            },
        },
        {
            "path": "/software/{name}/example-use",
            "method": "GET",
            "auth_required": True,
            "description": "Example usage text for a software package (may be empty string).",
            "response": {"example_use": "string"},
        },
        {
            "path": "/resources/{name}/software",
            "method": "GET",
            "auth_required": True,
            "description": "List all software available on a specific HPC resource with versions and load commands.",
            "response": {
                "type": "array",
                "items": {
                    "name": "string",
                    "version": "string",
                    "command": "string",
                    "load_commands?": "[string]",
                },
            },
        },
    ],
}


def _require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_app.config.get("REST_API_REQUIRE_AUTH", True):
            return f(*args, **kwargs)
        raw = request.headers.get("X-API-Key", "").strip()
        if not raw:
            return jsonify({"error": "Missing X-API-Key header"}), 401
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        key = APIKey.get_or_none(APIKey.key_hash == key_hash)
        if key is None or not key.is_valid():
            return jsonify({"error": "Invalid or expired API key"}), 403
        now = datetime.now(timezone.utc)
        APIKey.update(
            last_used_at=now,
            request_count=APIKey.request_count + 1,
        ).where(APIKey.id == key.id).execute()
        APIKeyLog.record(key_prefix=key.key_prefix, endpoint=request.path)
        # The label is quoted because it is free text; the raw key is never
        # logged.
        api_request_logger.info('%s "%s" %s', key.key_prefix, key.label, request.path)
        return f(*args, **kwargs)
    return decorated


def _ai_info(software_id):
    return AISoftwareInfo.get_or_none(AISoftwareInfo.software_id == software_id)


def _command_rows_by_entry(sr_ids):
    """All collected command rows for the given entries, grouped by
    SoftwareResource id — one query regardless of entry count."""
    grouped = defaultdict(list)
    if sr_ids:
        for row in SoftwareResourceCommand.select().where(
            SoftwareResourceCommand.software_resource_id.in_(sr_ids)
        ):
            grouped[row.software_resource_id_id].append(row)
    return grouped


def _resource_map(sw):
    entries = list(
        SoftwareResource.select(SoftwareResource, Resource)
        .where(SoftwareResource.software_id == sw.id)
        .join(Resource, on=(SoftwareResource.resource_id == Resource.id))
    )
    command_rows = _command_rows_by_entry([e.id for e in entries])
    edited = {
        (e.resource_name, e.software_version)
        for e in CommandEdit.select().where(
            CommandEdit.software_name == sw.software_name
        )
    }
    result = {}
    for sr in entries:
        resource_name = sr.resource_id.resource_name
        entry = {"version": sr.software_version}
        if sr.command:
            entry["command"] = sr.command
        load_commands = resolved_texts_from_rows(
            command_rows.get(sr.id, []),
            sr.command,
            (resource_name, sr.software_version) in edited,
        )
        if load_commands:
            entry["load_commands"] = load_commands
        result.setdefault(resource_name, []).append(entry)
    return result


def _container_list(software_id):
    rows = (
        SoftwareContainer.select(SoftwareContainer, Container, Resource)
        .where(SoftwareContainer.software_id == software_id)
        .join(Container)
        .join(Resource, on=(Container.resource_id == Resource.id))
        .dicts()
    )
    seen = set()
    containers = []
    for r in rows:
        key = (r.get("container_name", ""), r.get("container_file", ""))
        if key in seen:
            continue
        seen.add(key)
        containers.append({
            "container_name": r.get("container_name", ""),
            "container_file": r.get("container_file", ""),
            "resource": r.get("resource_name", ""),
            "versions": r.get("software_versions", ""),
            "command": r.get("command", ""),
            "notes": r.get("notes", ""),
        })
    return containers


def _software_to_dict(sw, include_containers=False):
    ai = _ai_info(sw.id)
    resources = _resource_map(sw)
    result = {
        "name": sw.software_name,
        "description": sw.software_description or (ai.ai_description if ai else ""),
        "research_field": ai.ai_research_field if ai else "",
        "software_type": ai.ai_software_type if ai else "",
        "tags": ai.ai_general_tags if ai else "",
        "web_page": sw.software_web_page,
        "documentation": sw.software_documentation,
        "resources": [{"resource": r, "versions": v} for r, v in resources.items()],
        "has_containers": SoftwareContainer.select()
            .where(SoftwareContainer.software_id == sw.id)
            .exists(),
    }
    if include_containers:
        result["containers"] = _container_list(sw.id)
    return result


@api_bp.route("/resources")
@_require_api_key
def list_resources():
    resources = Resource.select().order_by(Resource.resource_name)
    return jsonify([{"name": r.resource_name} for r in resources])


@api_bp.route("/software/search")
@_require_api_key
def search_software():
    q = request.args.get("q", "").strip()

    if q:
        ai_matches = (
            AISoftwareInfo.select(AISoftwareInfo.software_id)
            .where(
                AISoftwareInfo.ai_research_field.contains(q)
                | AISoftwareInfo.ai_research_area.contains(q)
                | AISoftwareInfo.ai_research_discipline.contains(q)
                | AISoftwareInfo.ai_general_tags.contains(q)
            )
        )
        software_query = Software.select().where(
            Software.software_name.contains(q)
            | Software.software_description.contains(q)
            | Software.id.in_(ai_matches)
        ).order_by(Software.software_name).limit(SEARCH_RESULT_LIMIT)
    else:
        software_query = (
            Software.select()
            .order_by(Software.software_name)
            .limit(SEARCH_RESULT_LIMIT)
        )

    return jsonify([_software_to_dict(sw) for sw in software_query])


@api_bp.route("/software/match-resources", methods=["POST"])
@_require_api_key
def match_resources():
    data = request.get_json() or {}
    packages = data.get("packages", [])
    fuzzy = data.get("fuzzy", True)

    if not packages:
        return jsonify({"matched": [], "unmatched": []})
    if len(packages) > MATCH_PACKAGES_LIMIT:
        return jsonify({
            "error": (
                f"Too many packages: {len(packages)} exceeds the limit of "
                f"{MATCH_PACKAGES_LIMIT} per request"
            )
        }), 400

    all_software = list(Software.select())
    software_names = [sw.software_name for sw in all_software]
    name_to_sw = {sw.software_name: sw for sw in all_software}

    matched = []
    unmatched = []

    def get_resources(sw):
        return list(set(
            r["resource_name"]
            for r in SoftwareResource.select(SoftwareResource, Resource)
            .where(SoftwareResource.software_id == sw.id)
            .join(Resource, on=(SoftwareResource.resource_id == Resource.id))
            .dicts()
        ))

    def get_description(sw):
        if sw.software_description:
            return sw.software_description
        ai = _ai_info(sw.id)
        return ai.ai_description if ai else ""

    for pkg in packages:
        pkg_matches = []
        pkg_lower = pkg.lower()

        if fuzzy:
            try:
                from rapidfuzz import process, fuzz
                # Pre-filter: only score candidates whose length is within 2.5x
                # of the query. WRatio uses partial_ratio internally, which gives
                # a score of 100 any time the query is a verbatim substring —
                # filtering by length ratio stops short queries from reaching
                # unrelated long names before scoring even begins.
                candidates = [n for n in software_names if n and len(pkg) / len(n) >= 0.4]
                results = process.extract(pkg, candidates, scorer=fuzz.WRatio, limit=10)
                for name, score, _ in results:
                    if score >= 85:
                        sw = name_to_sw[name]
                        pkg_matches.append({
                            "software_name": name,
                            "score": score,
                            "description": get_description(sw),
                            "resources": get_resources(sw),
                        })
            except ImportError:
                fuzzy = False

        if not fuzzy:
            for name in software_names:
                # Exact match or the catalog name starts with the query
                # (catches python→python3, r→r-base). Avoids the substring
                # trap where "r in pytorch" would be True.
                if name.lower() == pkg_lower or name.lower().startswith(pkg_lower):
                    sw = name_to_sw[name]
                    pkg_matches.append({
                        "software_name": name,
                        "score": 100,
                        "resources": get_resources(sw),
                    })

        pkg_matches.sort(key=lambda m: m["score"], reverse=True)

        if pkg_matches:
            matched.append({"package": pkg, "matches": pkg_matches})
        else:
            unmatched.append(pkg)

    return jsonify({"matched": matched, "unmatched": unmatched})


@api_bp.route("/software/<path:name>")
@_require_api_key
def get_software_details(name):
    sw = Software.get_or_none(Software.software_name == name)
    if sw is None:
        return jsonify({"error": f"Software '{name}' not found"}), 404
    return jsonify(_software_to_dict(sw, include_containers=True))


@api_bp.route("/software/<path:name>/containers")
@_require_api_key
def get_software_containers(name):
    sw = Software.get_or_none(Software.software_name == name)
    if sw is None:
        return jsonify({"error": f"Software '{name}' not found"}), 404
    return jsonify(_container_list(sw.id))


@api_bp.route("/software/<path:name>/example-use")
@_require_api_key
def get_software_example_use(name):
    sw = Software.get_or_none(Software.software_name == name)
    if sw is None:
        return jsonify({"error": f"Software '{name}' not found"}), 404
    ai = _ai_info(sw.id)
    return jsonify({"example_use": ai.ai_example_use if ai else ""})


@api_bp.route("/resources/<path:name>/software")
@_require_api_key
def get_resource_software(name):
    resource = Resource.get_or_none(Resource.resource_name == name)
    if resource is None:
        return jsonify({"error": f"Resource '{name}' not found"}), 404
    entries = list(
        SoftwareResource.select(SoftwareResource, Software)
        .where(SoftwareResource.resource_id == resource.id)
        .join(Software, on=(SoftwareResource.software_id == Software.id))
        .order_by(Software.software_name)
    )
    command_rows = _command_rows_by_entry([e.id for e in entries])
    edited = {
        (e.software_name, e.software_version)
        for e in CommandEdit.select().where(
            CommandEdit.resource_name == resource.resource_name
        )
    }
    result = []
    for sr in entries:
        software_name = sr.software_id.software_name
        item = {
            "name": software_name,
            "version": sr.software_version,
            "command": sr.command or "",
        }
        load_commands = resolved_texts_from_rows(
            command_rows.get(sr.id, []),
            sr.command,
            (software_name, sr.software_version) in edited,
        )
        if load_commands:
            item["load_commands"] = load_commands
        result.append(item)
    return jsonify(result)


@api_bp.route("/schema")
def get_schema():
    return jsonify(_SCHEMA)


@api_bp.app_errorhandler(HTTPException)
def _json_http_error(e):
    """Return errors on /api/ paths as JSON instead of the default HTML page.
    Registered app-wide so it also applies to routing 404/405s under /api/;
    non-API paths keep the default error response."""
    if request.path.startswith("/api/"):
        return jsonify({"error": e.description}), e.code or 500
    return e.get_response()
