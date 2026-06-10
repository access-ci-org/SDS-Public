import datetime

from flask import abort, render_template, request
from flask_login import current_user

from app.models import persistent_db
from app.models.banner import Banner
from app.logic.banners import VALID_SEVERITIES, validate_pages_input
from app.routes._decorators import admin_required
from . import banner_bp


def _now_iso():
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")


def _normalize_pages(raw_pages: list[str] | str) -> str:
    """Form posts arrive as a list (multiple checkboxes) or a single string.
    Returns the canonical CSV form for storage."""
    if isinstance(raw_pages, str):
        tokens = [p.strip() for p in raw_pages.split(",") if p.strip()]
    else:
        tokens = [p.strip() for p in raw_pages if p and p.strip()]
    return ",".join(tokens)


def _extract_form(form):
    """Pull and normalize the create/edit fields. Returns (fields, error)."""
    message = (form.get("message") or "").strip()
    severity = (form.get("severity") or "").strip()
    pages = _normalize_pages(form.getlist("pages") or form.get("pages") or [])
    is_active = form.get("is_active") == "on"
    dismissible = form.get("dismissible") == "on"

    if not message:
        return None, "Message is required."
    if severity not in VALID_SEVERITIES:
        return None, "Invalid severity."
    if not validate_pages_input(pages):
        return None, "Invalid page selection. Pick specific pages or 'All user-facing pages', not both."

    return {
        "message": message,
        "severity": severity,
        "pages": pages,
        "is_active": is_active,
        "dismissible": dismissible,
    }, None


def _render_tab(notice=None, notice_kind=None):
    """Render the banners tab fragment. Returned to HTMX swaps and also used
    by the initial settings page render via the same template inclusion."""
    all_banners = list(Banner.select().order_by(Banner.created_at.desc()))
    return render_template(
        "admin/banners_tab.html",
        all_banners=all_banners,
        notice=notice,
        notice_kind=notice_kind,
    )


@banner_bp.route("/admin/banners", methods=["POST"])
@admin_required
def create_banner():
    fields, error = _extract_form(request.form)
    if error:
        return _render_tab(notice=error, notice_kind="danger")

    with persistent_db.atomic():
        Banner.create(
            created_at=_now_iso(),
            created_by=current_user.username,
            **fields,
        )
    return _render_tab(notice="Banner created.", notice_kind="success")


@banner_bp.route("/admin/banners/<int:banner_id>/edit", methods=["POST"])
@admin_required
def edit_banner(banner_id):
    banner = Banner.get_or_none(Banner.id == banner_id)
    if banner is None:
        abort(404)

    fields, error = _extract_form(request.form)
    if error:
        return _render_tab(notice=error, notice_kind="danger")

    with persistent_db.atomic():
        for k, v in fields.items():
            setattr(banner, k, v)
        banner.updated_at = _now_iso()
        banner.save()
    return _render_tab(notice="Banner updated.", notice_kind="success")


@banner_bp.route("/admin/banners/<int:banner_id>/toggle", methods=["POST"])
@admin_required
def toggle_banner(banner_id):
    banner = Banner.get_or_none(Banner.id == banner_id)
    if banner is None:
        abort(404)

    with persistent_db.atomic():
        banner.is_active = not banner.is_active
        banner.updated_at = _now_iso()
        banner.save()
    return _render_tab()


@banner_bp.route("/admin/banners/<int:banner_id>/delete", methods=["POST"])
@admin_required
def delete_banner(banner_id):
    banner = Banner.get_or_none(Banner.id == banner_id)
    if banner is None:
        abort(404)

    with persistent_db.atomic():
        banner.delete_instance()
    return _render_tab(notice="Banner deleted.", notice_kind="success")
