"""
Banner display logic.

Banners are stored as markdown source. They render to HTML at request time
via convert_markdown_to_html (safe_mode escapes raw HTML / scripts).
"""
from app.models.banner import Banner
from app.logic.convertMarkdown import convert_markdown_to_html

VALID_SEVERITIES = {"info", "success", "warning", "danger"}
USER_FACING_PAGE_KEYS = {"software", "container", "login"}
# Sentinel value the "All user-facing pages" checkbox maps to. Deliberately
# specific (not just "all") so we can add other scope sentinels later — e.g.
# "all-admin" — without ambiguity.
ALL_KEYWORD = "all-user-facing"


def parse_pages(pages_field: str) -> set[str]:
    """Parse the comma-separated `pages` column into a set of page keys.

    Returns an empty set for unrecognized input rather than raising, so a
    malformed row in the DB skips display rather than crashing the request.
    """
    if not pages_field:
        return set()
    tokens = {t.strip() for t in pages_field.split(",") if t.strip()}
    if tokens == {ALL_KEYWORD}:
        return set(USER_FACING_PAGE_KEYS)
    if ALL_KEYWORD in tokens:
        return set()
    if not tokens.issubset(USER_FACING_PAGE_KEYS):
        return set()
    return tokens


def validate_pages_input(pages_field: str) -> bool:
    """Stricter check for write paths: mixing 'all' with specific keys is
    rejected, unknown keys are rejected, empty is rejected."""
    if not pages_field:
        return False
    tokens = {t.strip() for t in pages_field.split(",") if t.strip()}
    if not tokens:
        return False
    if tokens == {ALL_KEYWORD}:
        return True
    if ALL_KEYWORD in tokens:
        return False
    return tokens.issubset(USER_FACING_PAGE_KEYS)


def banners_for_page(page_key: str | None) -> list[dict]:
    """Return rendered banners for the given page, newest first.

    Returns an empty list if page_key is None (i.e. admin pages or any
    endpoint we don't map). Each dict has: id, severity, dismissible, html.
    """
    if page_key is None:
        return []

    out = []
    rows = (
        Banner
        .select()
        .where(Banner.is_active == True)  # noqa: E712 — peewee idiom
        .order_by(Banner.created_at.desc())
    )
    for b in rows:
        if page_key not in parse_pages(b.pages):
            continue
        html = convert_markdown_to_html(b.message or "").strip()
        if not html:
            continue
        out.append({
            "id": b.id,
            "severity": b.severity if b.severity in VALID_SEVERITIES else "info",
            "dismissible": bool(b.dismissible),
            "html": html,
        })
    return out
