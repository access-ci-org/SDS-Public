from pathlib import Path

from flask import render_template, request, jsonify, current_app

from app.logic.convertMarkdown import convert_markdown_to_html
from app.models.api_key import APIKey
from app.models.api_key_log import APIKeyLog
from ._decorators import admin_required
from .api_routes import _SCHEMA
from . import api_admin_bp

# The activity view renders the newest rows only; the complete history
# lives in the weekly-rotated file log.
ACTIVITY_PAGE_SIZE = 100

# Placeholder hosts used by the bundled guides. Replaced with this
# instance's public base URL before rendering, so every snippet is
# copy-paste-ready; the repo copies keep their generic placeholders.
_PLACEHOLDER_HOSTS = ("https://<your-sds-host>", "https://sds.example.edu")


def _rendered_guide(filename, public_base_url):
    text = (Path("docs") / filename).read_text(encoding="utf-8")
    for placeholder in _PLACEHOLDER_HOSTS:
        text = text.replace(placeholder, public_base_url)
    return convert_markdown_to_html(text)


@api_admin_bp.route("/admin/api")
@admin_required
def api_page():
    keys = list(APIKey.select().order_by(APIKey.created_at.desc()))

    key_filter = request.args.get("key", "").strip()
    show_activity = bool(key_filter) or request.args.get("tab") == "activity"
    log_query = APIKeyLog.select().order_by(APIKeyLog.id.desc())
    if key_filter:
        log_query = log_query.where(APIKeyLog.key_prefix == key_filter)
    log_total = log_query.count()
    log_entries = list(log_query.limit(ACTIVITY_PAGE_SIZE))

    # Behind the deployment proxy the request host loses the public port and
    # scheme, so a configured external_url wins over the request-derived one.
    base = current_app.config.get("EXTERNAL_URL") or request.host_url
    public_base_url = base.rstrip("/")
    return render_template(
        "admin/api_page.html",
        keys=keys,
        key_labels={k.key_prefix: k.label for k in keys},
        log_entries=log_entries,
        log_total=log_total,
        log_key_filter=key_filter,
        active_tab="activity" if show_activity else "keys",
        schema=_SCHEMA,
        public_base_url=public_base_url,
        mcp_guide_html=_rendered_guide("MCP.md", public_base_url),
        api_guide_html=_rendered_guide("API.md", public_base_url),
    )


@api_admin_bp.route("/admin/api/keys/create", methods=["POST"])
@admin_required
def create_api_key():
    label = request.form.get("label", "").strip()
    raw, instance = APIKey.generate(label=label)
    instance.save()
    return jsonify({
        "key": raw,
        "id": instance.id,
        "prefix": instance.key_prefix,
        "label": instance.label,
    })


@api_admin_bp.route("/admin/api/keys/<int:key_id>/revoke", methods=["POST"])
@admin_required
def revoke_api_key(key_id):
    updated = APIKey.update(is_active=False).where(APIKey.id == key_id).execute()
    if updated:
        return jsonify({"success": True})
    return jsonify({"error": "Key not found"}), 404


@api_admin_bp.route("/admin/api/keys/<int:key_id>/delete", methods=["POST"])
@admin_required
def delete_api_key(key_id):
    key = APIKey.get_or_none(APIKey.id == key_id)
    if key is None:
        return jsonify({"error": "Key not found"}), 404
    if key.is_active:
        return jsonify({"error": "Revoke the key before deleting it"}), 400
    key.delete_instance()
    return jsonify({"success": True})
