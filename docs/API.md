# SDS REST API

The SDS REST API lets external tools and scripts query the software catalog
programmatically. All endpoints live under `/api/v1`.

> The example values below are placeholders. Real responses reflect your
> instance's catalog.

## Base URL

- Behind the SDS container's web server: `https://<your-sds-host>/api/v1`
- Talking to the app directly (local/dev): `http://localhost:8080/api/v1`

The examples below use `https://sds.example.edu`, substitute your own host.

## Authentication

Every endpoint except `/schema` requires an API key, sent in the `X-API-Key`
header:

```
X-API-Key: sds_xxx...
```

Keys are created by an SDS admin under **Settings → API Keys**
(`/settings/api-keys`) in the web UI. The full key is shown once at creation.
Only a hash is stored, so a lost key can't be recovered; generate a new one
instead.

```bash
curl -H "X-API-Key: sds_xxxxxxxx" https://sds.example.edu/api/v1/resources
```

To disable authentication (development only), set in `config.yaml`:

```yaml
rest_api:
  require_auth: False
```

With auth disabled the `X-API-Key` header is ignored and every endpoint is open.

There is no rate limiting. Each key does record a last-used timestamp and a
cumulative request count, shown in the admin API Keys view. Every
authenticated request is also logged with the key prefix, key label,
endpoint, and timestamp: the newest 10,000 entries are kept in the
database, and complete history is appended to a weekly-rotated file log
under `data/state/logs/api/`.

---

## Discovery

#### `GET /api/v1/schema`

Returns a machine-readable description of the API: version, base URL, auth, and
every endpoint. It is the only endpoint that does not require a key.

```bash
curl https://sds.example.edu/api/v1/schema
```

**Response** (abridged)
```json
{
  "version": "1",
  "base_url": "/api/v1",
  "auth": {
    "type": "api_key",
    "header": "X-API-Key",
    "note": "All endpoints except /schema require a valid API key in the X-API-Key header."
  },
  "endpoints": [
    { "path": "/resources", "method": "GET", "auth_required": true, "description": "..." }
  ]
}
```

---

## Resources

#### `GET /api/v1/resources`

List all HPC clusters/resources tracked by this SDS instance.

```bash
curl -H "X-API-Key: sds_xxxxxxxx" https://sds.example.edu/api/v1/resources
```

**Response**
```json
[
  { "name": "resource1" },
  { "name": "resource2" }
]
```

---

#### `GET /api/v1/resources/<name>/software`

List all software available on a specific resource, with each version and its
load commands. `<name>` is matched exactly (case-sensitive). There is one entry
per version, so a package with several versions appears more than once.

```bash
curl -H "X-API-Key: sds_xxxxxxxx" \
  https://sds.example.edu/api/v1/resources/resource1/software
```

**Response**
```json
[
  {
    "name": "software1",
    "version": "1.0.0",
    "command": "module load software1/1.0.0",
    "load_commands": ["module load software1/1.0.0"]
  },
  {
    "name": "software2",
    "version": "2.3.0",
    "command": "module load software2/2.3.0",
    "load_commands": [
      "module load software2/2.3.0",
      "module load toolchain1/1.0 software2/2.3.0"
    ]
  }
]
```

`command` is the primary load command and always equals the first entry of
`load_commands`, which lists every published way to load that version. On
clusters with a hierarchical module tree, a single entry can load prerequisite
modules in the same line (`module load toolchain1/1.0 software2/2.3.0`).
Command edits made in the admin panel (hiding, replacing, or adding commands)
are reflected here. `load_commands` is omitted when the catalog has no load
commands for a version.

Returns `404` if no resource has that exact name.

---

## Software

#### `GET /api/v1/software/search?q=<query>`

Search the catalog by name, description, research field/area/discipline, or
tags. Matching is case-insensitive and substring-based. For fuzzy matching, use
the match-resources endpoint below.

- With `q`: returns matches ordered by name, capped at 100 results.
- Without `q`: returns the first 100 packages, ordered by name.

```bash
curl -H "X-API-Key: sds_xxxxxxxx" \
  "https://sds.example.edu/api/v1/software/search?q=soft"
```

**Response**
```json
[
  {
    "name": "software1",
    "description": "Short description of software1.",
    "research_field": "Example Field",
    "software_type": "CLI tool",
    "tags": "tag1, tag2",
    "web_page": "https://example.org/software1",
    "documentation": "https://example.org/software1/docs",
    "resources": [
      {
        "resource": "resource1",
        "versions": [
          {
            "version": "1.0.0",
            "command": "module load software1/1.0.0",
            "load_commands": ["module load software1/1.0.0"]
          }
        ]
      }
    ],
    "has_containers": true
  }
]
```

`description` falls back to the AI-generated description when there is no curated
one. A version's `command` is its primary load command; `load_commands` lists
every published way to load it, primary first (see the resources endpoint
above). Both keys are omitted when the catalog has no load commands for that
version.

---

#### `GET /api/v1/software/<name>`

Full details for one package by exact name. The name match is case-insensitive
(catalog names use a case-insensitive collation); slashes in the name are
allowed. Includes everything from the search response plus a `containers` array.

```bash
curl -H "X-API-Key: sds_xxxxxxxx" \
  https://sds.example.edu/api/v1/software/software1
```

**Response**
```json
{
  "name": "software1",
  "description": "Short description of software1.",
  "research_field": "Example Field",
  "software_type": "CLI tool",
  "tags": "tag1, tag2",
  "web_page": "https://example.org/software1",
  "documentation": "https://example.org/software1/docs",
  "resources": [
    {
      "resource": "resource1",
      "versions": [
        {
          "version": "1.0.0",
          "command": "module load software1/1.0.0",
          "load_commands": ["module load software1/1.0.0"]
        }
      ]
    }
  ],
  "has_containers": true,
  "containers": [
    {
      "container_name": "software1-1.0.0.sif",
      "container_file": "/path/to/containers/software1-1.0.0.sif",
      "resource": "resource1",
      "versions": "1.0.0",
      "command": "singularity exec software1-1.0.0.sif software1",
      "notes": "Example note"
    }
  ]
}
```

Returns `404` if no package has that exact name.

---

#### `GET /api/v1/software/<name>/containers`

List the container images available for a package, deduplicated by
(name, file). Returns an empty array if the package exists but has no
containers.

```bash
curl -H "X-API-Key: sds_xxxxxxxx" \
  https://sds.example.edu/api/v1/software/software1/containers
```

**Response**
```json
[
  {
    "container_name": "software1-1.0.0.sif",
    "container_file": "/path/to/containers/software1-1.0.0.sif",
    "resource": "resource1",
    "versions": "1.0.0",
    "command": "singularity exec software1-1.0.0.sif software1",
    "notes": "Example note"
  }
]
```

Returns `404` if no package has that exact name.

---

#### `GET /api/v1/software/<name>/example-use`

Return example-usage text (markdown) for a package. If the package exists, this
returns `200`; when there is no example text, `example_use` is an empty string.

```bash
curl -H "X-API-Key: sds_xxxxxxxx" \
  https://sds.example.edu/api/v1/software/software1/example-use
```

**Response**
```json
{ "example_use": "# Using software1\n\nmodule load software1/1.0.0\nsoftware1 --help" }
```

Returns `404` only if the package itself does not exist.

---

#### `POST /api/v1/software/match-resources`

Match a list of package names against the catalog and show which resources
provide each. Useful for checking HPC availability from a `requirements.txt` or
import list. Packages with no match are returned separately in `unmatched`.

**Request body**
```json
{
  "packages": ["pkg1", "pkg2", "pkg3"],
  "fuzzy": true
}
```

- `packages`: list of package/import names (required, max 500 per request). An
  empty or missing list returns `{"matched": [], "unmatched": []}`; more than
  500 entries returns a `400` error.
- `fuzzy`: when `true` (default), uses fuzzy matching so a shortened or variant
  name can match a longer catalog entry. When `false`, matches only catalog
  names that equal or start with the query (for example `soft` matches
  `software1`).

```bash
curl -X POST https://sds.example.edu/api/v1/software/match-resources \
  -H "X-API-Key: sds_xxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"packages": ["pkg1", "pkg2", "pkg3"], "fuzzy": true}'
```

**Response** (fuzzy)
```json
{
  "matched": [
    {
      "package": "pkg1",
      "matches": [
        {
          "software_name": "software1",
          "score": 90.0,
          "description": "Short description of software1.",
          "resources": ["resource1"]
        }
      ]
    },
    {
      "package": "pkg2",
      "matches": [
        {
          "software_name": "software2",
          "score": 100.0,
          "description": "Short description of software2.",
          "resources": ["resource1", "resource2"]
        }
      ]
    }
  ],
  "unmatched": ["pkg3"]
}
```

Matches are sorted by `score`, highest first. With `fuzzy: false`, each match
omits `description` and reports `score: 100`:

```json
{
  "matched": [
    { "package": "soft", "matches": [
      { "software_name": "software1", "score": 100, "resources": ["resource1"] }
    ] }
  ],
  "unmatched": []
}
```

The body must be JSON sent with `Content-Type: application/json`; otherwise the
server returns `415` (wrong content type) or `400` (malformed JSON).

---

## Error responses

All error responses are JSON objects of the form `{ "error": "<message>" }`.

| Status | When |
|---|---|
| `400` | Malformed JSON body, or more than 500 packages (`match-resources`) |
| `401` | Missing `X-API-Key` header |
| `403` | API key is invalid, expired, or revoked |
| `404` | Named software or resource not found |
| `415` | `match-resources` body sent without `Content-Type: application/json` |
