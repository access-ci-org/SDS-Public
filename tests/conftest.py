"""
Backend test fixtures.

The SDS app is module-level Flask (no factory pattern). Fixtures work by:
- Pointing both Peewee databases at fresh tmp files per-test via `db.init()`
- Creating tables in the fresh DBs
- Using `flask_app.test_client()` for requests
- Resetting the `TABLE_INFO` singleton between tests (order-dependency hazard)
- Mocking external network calls so no test hits the network unintentionally

When `Users` later moves from the transient DB to the persistent DB, only
the model list below needs updating.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The app reads config.yaml and other paths relative to cwd.
os.chdir(REPO_ROOT)

# Stub libmagic-dependent `magic` so test imports of parser modules don't
# require the system libmagic library. Tests that need the parser only call
# pure functions; `is_text_file` (the only consumer of magic) is not under test.
sys.modules.setdefault("magic", MagicMock())

# Ensure a config.yaml exists before importing the app. Local devs have one;
# CI does not, so we copy the test fixture into place.
_REAL_CONFIG = REPO_ROOT / "config.yaml"
_FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config_test.yaml"
if not _REAL_CONFIG.exists():
    if not _FIXTURE_CONFIG.exists():
        raise RuntimeError(
            "tests/fixtures/config_test.yaml is missing — needed when no real "
            "config.yaml is present (e.g. CI)"
        )
    shutil.copy(_FIXTURE_CONFIG, _REAL_CONFIG)

# Now safe to import. This triggers app/__init__.py module-level setup
# (config loading, blueprint registration, etc.).
from app import app as _flask_app  # noqa: E402
from app.logic import table as _table_module  # noqa: E402
from app.models import db, persistent_db  # noqa: E402
from app.models.aiSoftwareInfo import AISoftwareInfo  # noqa: E402
from app.models.command_edit import CommandEdit  # noqa: E402
from app.models.containers import Container  # noqa: E402
from app.models.resource import Resource  # noqa: E402
from app.models.software import Software  # noqa: E402
from app.models.softwareContainer import SoftwareContainer  # noqa: E402
from app.models.softwareResource import SoftwareResource  # noqa: E402
from app.models.software_edit import SoftwareEdit  # noqa: E402
from app.models.banner import Banner  # noqa: E402
from app.models.users import Users  # noqa: E402


TRANSIENT_MODELS = [
    Resource,
    Software,
    SoftwareResource,
    AISoftwareInfo,
    Container,
    SoftwareContainer,
    Users,  # planned to move to persistent DB later
]

PERSISTENT_MODELS = [
    SoftwareEdit,
    CommandEdit,
    Banner,
]


# --- Session-wide ---

@pytest.fixture
def flask_app():
    """Direct access to the Flask app object. Tests usually want `client` instead."""
    return _flask_app


# --- Autouse hygiene ---

@pytest.fixture(autouse=True)
def reset_table_info_singleton():
    """TABLE_INFO is a module-level cache. Reset before AND after each test
    to eliminate test-order dependency."""
    _table_module.TABLE_INFO = None
    yield
    _table_module.TABLE_INFO = None


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    """Block accidental external HTTP. Tests that need a mocked response
    should patch the specific call site explicitly."""
    def _fail(*args, **kwargs):
        raise RuntimeError(
            "Test made an unmocked external HTTP request. "
            "Patch the specific call site (e.g. requests.get) in your test."
        )
    monkeypatch.setattr("requests.get", _fail)
    monkeypatch.setattr("requests.post", _fail)
    monkeypatch.setattr(
        "app.logic.sdsVersions.get_pending_updates",
        lambda *a, **kw: [],
    )


@pytest.fixture(autouse=True)
def reset_app_config():
    """Start each test with a known config. Saves the import-time config,
    overrides to test defaults, restores on teardown."""
    saved = dict(_flask_app.config)
    _flask_app.config.update(
        TESTING=True,
        USE_API=False,
        USE_AI_INFO=False,
        USE_CURATED_INFO=False,
        HIDE_DATA=[],
        SHOW_CONTAINER_PAGE=True,
        IFRAME=False,
        EXTERNAL_ANALYTICS="",
        SHARE_WITH_DEVS=False,
        SHARE_WITH_OTHERS=False,
    )
    yield
    _flask_app.config.clear()
    _flask_app.config.update(saved)


# --- Database ---

@pytest.fixture
def databases(tmp_path):
    """Point both Peewee databases at fresh tmp files for one test."""
    transient_path = tmp_path / "sds_db.db"
    persistent_path = tmp_path / "sds_persistent.db"

    if not db.is_closed():
        db.close()
    if not persistent_db.is_closed():
        persistent_db.close()

    db.init(str(transient_path))
    persistent_db.init(str(persistent_path))

    db.connect(reuse_if_open=True)
    persistent_db.connect(reuse_if_open=True)
    db.create_tables(TRANSIENT_MODELS, safe=True)
    persistent_db.create_tables(PERSISTENT_MODELS, safe=True)

    yield

    if not db.is_closed():
        db.close()
    if not persistent_db.is_closed():
        persistent_db.close()


# --- Clients ---

@pytest.fixture
def client(databases):
    """Anonymous Flask test client."""
    with _flask_app.test_client() as c:
        yield c


def _login_via_session(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


@pytest.fixture
def user_client(client, user_account):
    _login_via_session(client, user_account)
    return client


@pytest.fixture
def admin_client(client, admin_account):
    _login_via_session(client, admin_account)
    return client


# --- User factories ---

@pytest.fixture
def make_user(databases):
    counter = {"n": 0}

    def _make(username=None, password="userpass", is_admin=False, email=None):
        counter["n"] += 1
        if username is None:
            username = f"user_{counter['n']}"
        if email is None:
            email = f"{username}@test.local"
        return Users.create(
            username=username,
            password=Users.hash_password(password),
            is_admin=is_admin,
            email=email,
        )

    return _make


@pytest.fixture
def user_account(make_user):
    return make_user(username="user1", password="userpass", is_admin=False)


@pytest.fixture
def admin_account(make_user):
    return make_user(username="admin1", password="adminpass", is_admin=True)


# --- Data builders ---

@pytest.fixture
def make_resource(databases):
    counter = {"n": 0}

    def _make(name=None):
        counter["n"] += 1
        if name is None:
            name = f"cluster_{counter['n']}"
        return Resource.create(resource_name=name)

    return _make


@pytest.fixture
def make_software(databases):
    counter = {"n": 0}

    def _make(name=None, description="", web_page="", documentation="", use_link=""):
        counter["n"] += 1
        if name is None:
            name = f"pkg_{counter['n']}"
        return Software.create(
            software_name=name,
            software_description=description,
            software_web_page=web_page,
            software_documentation=documentation,
            software_use_link=use_link,
        )

    return _make


@pytest.fixture
def make_software_resource(databases):
    def _make(software, resource, version="1.0.0", command=""):
        return SoftwareResource.create(
            software_id=software,
            resource_id=resource,
            software_version=version,
            command=command,
        )

    return _make


@pytest.fixture
def make_ai(databases):
    def _make(software, **fields):
        defaults = {
            "ai_description": "",
            "ai_software_type": "",
            "ai_software_class": "",
            "ai_research_field": "",
            "ai_research_area": "",
            "ai_research_discipline": "",
            "ai_core_features": "",
            "ai_general_tags": "",
            "ai_example_use": "",
        }
        defaults.update(fields)
        return AISoftwareInfo.create(software_id=software, **defaults)

    return _make


@pytest.fixture
def make_edit(databases):
    def _make(software_name, **fields):
        # Accept auto_values as a dict for ergonomic tests; serialize to JSON
        # before insert.
        if "auto_values" in fields and isinstance(fields["auto_values"], dict):
            import json as _json
            fields["auto_values"] = _json.dumps(fields["auto_values"])
        return SoftwareEdit.create(software_name=software_name, **fields)

    return _make


@pytest.fixture
def make_command_edit(databases):
    def _make(software_name, resource_name, software_version, command=None,
              auto_command=None, edited_by=None, edited_at=None):
        return CommandEdit.create(
            software_name=software_name,
            resource_name=resource_name,
            software_version=software_version,
            command=command,
            auto_command=auto_command,
            edited_by=edited_by,
            edited_at=edited_at,
        )

    return _make


@pytest.fixture
def make_container(databases):
    def _make(name, resource, definition_file="", container_file="", notes=""):
        return Container.create(
            container_name=name,
            resource_id=resource,
            definition_file=definition_file,
            container_file=container_file,
            notes=notes,
        )

    return _make


# --- Seeded scenarios ---

@pytest.fixture
def seeded_db(make_resource, make_software, make_software_resource, make_ai):
    """Minimal known data: one resource, one software with version + command + AI info."""
    resource = make_resource(name="test_cluster")
    software = make_software(name="testpkg", description="A test package")
    sr = make_software_resource(
        software, resource,
        version="1.0.0",
        command="module load testpkg/1.0.0",
    )
    ai = make_ai(
        software,
        ai_description="AI description for testpkg",
        ai_software_type="library",
        ai_research_discipline="Computer Science",
        ai_general_tags="test, pkg",
    )
    return {
        "resource": resource,
        "software": software,
        "software_resource": sr,
        "ai": ai,
    }


# --- Fixture-file helpers ---

FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


@pytest.fixture
def fixture_path():
    """Return absolute path to a file under tests/fixtures/."""
    def _path(relative):
        p = FIXTURES_DIR / relative
        if not p.exists():
            raise FileNotFoundError(f"Fixture missing: {p}")
        return p

    return _path
