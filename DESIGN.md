# Design: Admin Front-End Editing

## Goal

Allow admins to edit software metadata from the browser without touching backend files or
re-running the data pipeline. Edits must survive database resets.

This feature is designed to be merged with the `mcp` branch, which introduces
`sds_persistent.db`. The override storage described here lives in that same persistent
database.

---

## Context: How Data Flows In Today

The pipeline has three layers, applied in order during `reset_database.py`:

```
1. Parsed data       spider/container/CSV → software_name, versions, commands,
                                            description (if present in module data)

2. API curated data  remote SDS API      → software_web_page, software_documentation,
                                            software_use_link, software_description
                                            (only fills if field is still empty)

3. AISoftwareInfo    remote SDS API      → ai_description, ai_software_type,
                                            ai_software_class, ai_research_field,
                                            ai_research_area, ai_research_discipline,
                                            ai_core_features, ai_general_tags,
                                            ai_example_use
```

Every reset drops and rebuilds `sds_db.db` from scratch, so any edits written directly
to that database are lost.

---

## Editable Scope

Admins can edit every field about a software entry **except**:

- `software_name` — the identity key, set by the parser
- Resource availability — which clusters it appears on, versions, load commands
  (these come from `SoftwareResource` / `SoftwareContainer` and reflect cluster state)

Everything else is in scope:

| Field | Table | Currently populated by |
|---|---|---|
| `software_description` | Software | Spider data or API |
| `software_web_page` | Software | API curated |
| `software_documentation` | Software | API curated |
| `software_use_link` | Software | API curated |
| `ai_description` | AISoftwareInfo | API AI |
| `ai_software_type` | AISoftwareInfo | API AI |
| `ai_software_class` | AISoftwareInfo | API AI |
| `ai_research_field` | AISoftwareInfo | API AI |
| `ai_research_area` | AISoftwareInfo | API AI |
| `ai_research_discipline` | AISoftwareInfo | API AI |
| `ai_core_features` | AISoftwareInfo | API AI |
| `ai_general_tags` | AISoftwareInfo | API AI |
| `ai_example_use` | AISoftwareInfo | API AI or markdown file |

---

## Persistent Override Layer

### The approach

Admin edits live in a new `SoftwareEdit` table in `sds_persistent.db`. This database is
never wiped. At the end of every `reset_database.py` run, an `apply_overrides()` step
reads all rows from `SoftwareEdit` and writes non-null values into the freshly rebuilt
`sds_db.db`.

The full priority stack after a reset:

```
spider/container parsed  →  API curated/AI  →  SoftwareEdit  (last wins)
```

Between resets, saving an edit writes through to `sds_db.db` immediately so the display
reflects it without a reset.

### SoftwareEdit table schema

One row per software entry. `NULL` means no override for that field — the auto-populated
value is used. An explicit empty string `""` is a valid override (it clears the field).

```
software_name          TEXT  PRIMARY KEY
description            TEXT  NULL
web_page               TEXT  NULL
documentation          TEXT  NULL
use_link               TEXT  NULL
ai_description         TEXT  NULL
ai_software_type       TEXT  NULL
ai_software_class      TEXT  NULL
ai_research_field      TEXT  NULL
ai_research_area       TEXT  NULL
ai_research_discipline TEXT  NULL
ai_core_features       TEXT  NULL
ai_general_tags        TEXT  NULL
ai_example_use         TEXT  NULL
edited_at              TEXT
edited_by              TEXT
```

A single flat table is used rather than one row per field. This keeps queries simple and
makes bulk import/export straightforward. If per-field audit history is needed in the
future the schema can be versioned at that point.

### NULL vs. empty string semantics

This distinction matters and must be enforced consistently throughout the backend:

- `NULL` — no override; use whatever the pipeline produced
- `""` — explicit override to an empty value (hides the field from users)
- Any other string — override with that value

---

## Retiring the Existing CSV and Markdown Override Mechanisms

### software.csv

The `software.csv` file is currently a backend-level override — admins edit a file on
disk and re-run the pipeline. The `SoftwareEdit` table replaces this entirely.

**Migration path**: The CSV is no longer applied as a pipeline step. Instead, an import
route accepts the existing CSV format and writes rows into `SoftwareEdit`. Existing
deployments do a one-time import via the admin UI, after which the CSV file is inert.

`reset_database.py` will emit a warning if `software.csv` is present and non-empty,
directing admins to use the import UI.

### software_uses/ markdown files

Markdown files in `./software_uses/` currently override `ai_example_use` at reset time.
With `SoftwareEdit`, there are two competing mechanisms for the same field.

**Migration path**: During `apply_overrides()`, if a markdown file exists for a software
entry and `SoftwareEdit` has no row (or a NULL `ai_example_use`) for that entry, the
markdown content is written into `SoftwareEdit.ai_example_use`. After one reset, the
markdown file is effectively imported and the DB is the source of truth.

This is a one-way migration — the file is not deleted, but it is not consulted again
once an override row exists. Admins are notified in the UI that legacy markdown files
have been imported.

---

## Backend API

All routes require an active admin session (`@admin_required`).

### Single software

```
GET  /admin/edit/software/<name>
```
Returns the current displayed value, source (`parsed` | `api` | `admin`), and the raw
auto-populated value for every editable field. The auto value is always returned even
when an admin override is active, so the admin can compare before reverting.

Response shape:
```json
{
  "software_name": "pytorch",
  "fields": {
    "description": {
      "value": "Admin-written description",
      "source": "admin",
      "auto_value": "PyTorch description from API"
    },
    "web_page": {
      "value": "https://pytorch.org",
      "source": "api",
      "auto_value": "https://pytorch.org"
    }
  },
  "edited_at": "2026-05-28T14:32:00",
  "edited_by": "sandesh"
}
```

```
PUT  /admin/edit/software/<name>
```
Saves one or more field overrides. Only fields present in the request body are written.
Omitting a field leaves its current override (or NULL) unchanged.

```
DELETE  /admin/edit/software/<name>/<field>
```
Reverts a single field to NULL (removes the override). The auto-populated value
immediately becomes the displayed value.

### Bulk operations

```
POST  /admin/edit/import
```
Accepts JSON (primary) or CSV (legacy support). Upserts rows into `SoftwareEdit`.

**JSON format**: array of objects, `software_name` required, all other fields optional.
Omitting a field leaves any existing override untouched. Explicit `null` clears the
override for that field (revert to auto).

```json
[
  {
    "software_name": "pytorch",
    "description": "Open source machine learning framework.",
    "web_page": "https://pytorch.org"
  },
  {
    "software_name": "gromacs",
    "ai_software_type": null
  }
]
```

**CSV format** (legacy, matches existing `software.csv` column names):
```
software,software_description,software_web_page,software_documentation,software_use_link
pytorch,Open source machine learning framework.,https://pytorch.org,,
```
Only the four core Software fields are supported via CSV. AI fields require JSON.

```
GET  /admin/edit/export
```
Returns a JSON array of all non-empty `SoftwareEdit` rows. Round-trip safe: export →
edit → import produces identical state.

### Admin summary

```
GET  /admin/edit/summary
```
Returns counts and lists to support the missing-metadata overview:

```json
{
  "total_software": 842,
  "no_description": 134,
  "no_web_page": 201,
  "no_documentation": 189,
  "no_override_at_all": 310,
  "recently_edited": [
    { "software_name": "pytorch", "edited_at": "...", "edited_by": "sandesh" }
  ]
}
```

---

## Frontend

### Stack addition: HTMX

HTMX (~14KB, CDN, no build step) is added to `base.html`. It is used exclusively for
admin editing interactions. The main software table, DataTables, Bootstrap, and all
existing JavaScript are untouched.

HTMX is the right fit here because the editing workflow is entirely server-rendered:
the server returns HTML fragments in response to user actions rather than JSON that
JavaScript has to interpret and render. No client-side state management is needed.

DataTables is not used in the admin editing UI. It is the right tool for the
researcher-facing software table; it is not the right tool for an admin form workflow.

### Two UI surfaces

**Surface 1 — Inline editing in the software details modal**

The existing software details modal (opened from the main table) gains an admin-only
edit panel at the bottom, visible only when an admin is logged in. This is the primary
path for editing a single software entry (Stories 1, 2, 4, 6).

Interaction flow:
```
Admin opens software details modal
  → Edit panel shows all editable fields with current values
  → Fields with admin overrides show a badge ("edited") and a Revert link
  → Fields with no override show source badge ("from API", "from parser")
  → Admin edits one or more fields
  → Save button → hx-put → server saves + returns updated panel HTML
  → Panel refreshes in place, badges update
  → Revert link → hx-delete → server clears field + returns updated row
```

**Surface 2 — Admin overview page `/admin/software`**

A dedicated admin-only page for bulk operations and finding gaps (Story 7). Linked from
the settings navigation.

Sections:
- **Summary cards**: total software, missing descriptions, missing web pages, missing
  docs, entries with no overrides at all
- **Software list**: server-rendered table, filterable by name and by "missing field"
  status, paginated server-side (no DataTables)
  - Each row links to the software details modal with the edit panel pre-opened
  - Inline edit of description directly in the row for quick single-field edits
- **Import / Export**: drag-and-drop JSON upload, CSV upload, export-all button

### Auth and visibility

All admin UI elements are conditionally rendered by Jinja (`{% if current_user.is_admin %}`).
Admin routes return 403 for non-admin sessions. There is no client-side auth logic.

---

## User Stories Addressed

| Story | How addressed |
|---|---|
| Post-reset cleanup (edit missing fields) | Inline edit panel in modal; edits survive reset via apply_overrides() |
| Fix bad AI classification | Same inline panel; all AI fields editable |
| Migrate from software.csv | Import route accepts existing CSV format |
| Revert a bad edit | Per-field DELETE route; Revert link in UI |
| See provenance before editing | GET response includes source + auto_value for every field |
| Multi-admin visibility | edited_by + edited_at shown in edit panel |
| Find software with missing metadata | /admin/software summary + filterable list |
| Export for version control | GET /admin/edit/export; JSON round-trips cleanly |
| Software renamed upstream | No issue; SoftwareEdit keyed by name, old row simply has no SoftwareResource rows |
| Markdown files continue to work | One-time migration into SoftwareEdit on first reset |

---

## Out of Scope

- Editing software availability (which cluster a package is on, versions, load commands)
- Editing `software_name`
- Full audit history / change log (single edited_at/edited_by per row only)
- Container notes editing (Container.notes) — different data model, deferred
- Per-user edit permissions (all admins have full edit access)
- Real-time collaborative editing

---

## Build Order

1. `SoftwareEdit` model in `app/models/software_edit.py`, backed by `sds_persistent.db`
2. `apply_overrides()` function; integrate into `reset_database.py` as final step
3. Markdown and CSV migration logic within `apply_overrides()`
4. REST routes in `app/routes/edit_routes.py` (GET/PUT single, DELETE field,
   POST import, GET export, GET summary)
5. Add HTMX to `base.html`
6. Admin edit panel in software details modal (`softwareDetailsModal.js` +
   `modals/softwareDetailsModal.html`)
7. `/admin/software` overview page (template + route)
8. Wire admin link into settings navigation
