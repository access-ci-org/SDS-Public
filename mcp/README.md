# SDS MCP Server (`sds-mcp`)

Python package for the SDS MCP server. It exposes the SDS software catalog to AI
clients over the [Model Context Protocol](https://modelcontextprotocol.io),
wrapping the SDS REST API (`/api/v1`).

**Connecting an AI client** (Claude, Codex, VS Code, and others) and the list of
tools it exposes are documented in `docs/MCP.md`. This README covers the package
itself: installing, configuring, and running the server.

## Install (development)

```bash
pip install -e .
```

This provides the `sds-mcp` console script.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_TRANSPORT` | `stdio` | `stdio` (local) or `streamable-http` (hosted). |
| `MCP_HOST` | `127.0.0.1` | Bind host (streamable-http only). |
| `MCP_PORT` | `9000` | Bind port (streamable-http only). |
| `SDS_API_URL` | `http://localhost:5000/api/v1` | Base URL of the SDS REST API; set to your app's port. |
| `SDS_API_KEY` | _(empty)_ | API key, sent as `X-API-Key` (stdio mode only). |

In `streamable-http` mode the server forwards each request's
`Authorization: Bearer <key>` on to the REST API as `X-API-Key`, so `SDS_API_KEY`
is used only in stdio mode.

## Run it manually

```bash
# stdio: waits on stdin
SDS_API_URL=http://localhost:8080/api/v1 SDS_API_KEY=sds_xxxxxxxx sds-mcp

# streamable-http: serves on MCP_HOST:MCP_PORT
MCP_TRANSPORT=streamable-http MCP_PORT=9000 \
  SDS_API_URL=http://localhost:8080/api/v1 sds-mcp
```

## In the SDS container

The SDS container runs this server under supervisord in `streamable-http` mode on
`127.0.0.1:9000`, and nginx reverse-proxies it at `/mcp`. No `SDS_API_KEY` is set
in the container. Each user authenticates with their own key via the
`Authorization: Bearer` header, which the server forwards as `X-API-Key`. That
hosted `https://<host>/mcp` endpoint is what clients connect to (see
`docs/MCP.md`).

## Troubleshooting

**"Server disconnected" in a client:** run the `sds-mcp` command yourself to see
the error, confirm the package is installed (`pip install -e .`), and for stdio
clients use an absolute path to the console script if it isn't on `PATH`.
