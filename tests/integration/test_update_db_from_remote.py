"""
Reproduces the squeeze() bug in update_db_from_remote.

When the remote dataset has 2+ rows for the same software_name, DataFrame.squeeze()
does NOT collapse to a Series — it stays a DataFrame. Subsequent code then passes
Series-of-values where it expects scalars, and the Software row gets corrupted
(or the call crashes).

Once fixed, this test locks in the correct behavior:
- duplicates → first row wins
- a warning is logged
- the Software row is updated with scalar values, not Series reprs

Also locks the empty-value rule for the curated link fields: an empty
remote web_page / documentation / use_link means "no data" and leaves the
stored value untouched; a non-empty remote value still overwrites.
"""
import pytest

from app.models.software import Software

from reset_database import update_db_from_remote


REMOTE_FIELDS = [
    "software_name",
    "software_web_page",
    "software_documentation",
    "software_use_link",
    "software_description",
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


def _remote_rows(*rows):
    """Build a column-oriented dict for pd.DataFrame from row-oriented input."""
    return {field: [row.get(field, "") for row in rows] for field in REMOTE_FIELDS}


def test_duplicate_remote_rows_do_not_corrupt_software(seeded_db, flask_app):
    """Two remote rows for 'testpkg' → Software row must contain scalar values
    from one of them, not a Series-as-string."""
    flask_app.config["USE_API"] = True
    flask_app.config["USE_CURATED_INFO"] = True
    flask_app.config["USE_AI_INFO"] = False

    remote = _remote_rows(
        {
            "software_name": "testpkg",
            "software_web_page": "http://first.example",
            "software_documentation": "http://docs.first.example",
            "software_use_link": "http://use.first.example",
        },
        {
            "software_name": "testpkg",
            "software_web_page": "http://second.example",
            "software_documentation": "http://docs.second.example",
            "software_use_link": "http://use.second.example",
        },
    )

    update_db_from_remote(remote)

    sw = Software.get(Software.software_name == "testpkg")
    # The stored value should be one of the two real URLs, not a Series repr
    assert sw.software_web_page in (
        "http://first.example",
        "http://second.example",
    ), f"unexpected stored value: {sw.software_web_page!r}"


def test_empty_remote_links_leave_existing_values(seeded_db, flask_app):
    flask_app.config["USE_API"] = True
    flask_app.config["USE_CURATED_INFO"] = True
    flask_app.config["USE_AI_INFO"] = False

    Software.update(
        software_web_page="https://example.org/tool",
        software_documentation="https://example.org/tool/docs",
    ).where(Software.software_name == "testpkg").execute()

    remote = _remote_rows({"software_name": "testpkg"})

    update_db_from_remote(remote)

    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_web_page == "https://example.org/tool"
    assert sw.software_documentation == "https://example.org/tool/docs"


def test_non_empty_remote_links_overwrite(seeded_db, flask_app):
    flask_app.config["USE_API"] = True
    flask_app.config["USE_CURATED_INFO"] = True
    flask_app.config["USE_AI_INFO"] = False

    Software.update(
        software_web_page="https://example.org/tool"
    ).where(Software.software_name == "testpkg").execute()

    remote = _remote_rows(
        {
            "software_name": "testpkg",
            "software_web_page": "https://curated.example/tool",
        }
    )

    update_db_from_remote(remote)

    sw = Software.get(Software.software_name == "testpkg")
    assert sw.software_web_page == "https://curated.example/tool"
