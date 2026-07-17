# SDS MCP Server

The SDS MCP server lets an AI assistant (Claude, Codex, VS Code, and other
[MCP](https://modelcontextprotocol.io) clients) answer natural-language
questions about the HPC software in an SDS instance: versions, load commands,
containers, and which clusters carry a given set of packages.

Your institution runs this server as part of its SDS deployment, so there's
nothing to install. You just point your AI client at it with an API key.

## Get an API key

Ask your SDS administrator for a key. They create it under **Settings → API
Keys** in the SDS web UI. It looks like `sds_xxxxxxxx`. Keep it secret; the full
key is shown only once.

---

## Connect your client

The SDS MCP endpoint is a standard streamable-HTTP server:

```
https://<your-sds-host>/mcp
```

Authenticate with your key in an `Authorization: Bearer` header. The exact
configuration differs by client. Use the one for yours below, and replace
`<your-sds-host>` and `sds_xxxxxxxx` with your instance's URL and your key.

### Claude Code

```bash
claude mcp add --transport http sds https://<your-sds-host>/mcp \
  --header "Authorization: Bearer sds_xxxxxxxx"
```

### Claude Desktop

Claude Desktop can't reach a remote server directly, so it uses the `mcp-remote`
bridge (needs Node.js for `npx`). Add to `claude_desktop_config.json`, then fully
quit and reopen Claude Desktop:

```json
{
  "mcpServers": {
    "sds": {
      "command": "npx",
      "args": [
        "mcp-remote", "https://<your-sds-host>/mcp",
        "--header", "Authorization:${AUTH_HEADER}"
      ],
      "env": { "AUTH_HEADER": "Bearer sds_xxxxxxxx" }
    }
  }
}
```

The key lives in the `env` block (not `args`) so the space in `Bearer <key>`
doesn't break the command on Windows.

### Codex CLI

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.sds]
url = "https://<your-sds-host>/mcp"
bearer_token_env_var = "SDS_API_KEY"
```

Then export your key. Codex adds the `Bearer` prefix itself, so the variable
holds only the key:

```bash
export SDS_API_KEY="sds_xxxxxxxx"
```

### VS Code

Add to `.vscode/mcp.json` (workspace) or your user `mcp.json`. VS Code prompts
for the key the first time and stores it securely:

```json
{
  "inputs": [
    { "type": "promptString", "id": "sds-key", "description": "SDS API Key", "password": true }
  ],
  "servers": {
    "sds": {
      "type": "http",
      "url": "https://<your-sds-host>/mcp",
      "headers": { "Authorization": "Bearer ${input:sds-key}" }
    }
  }
}
```

### Other MCP clients

Any client that supports remote (HTTP / streamable-HTTP) MCP servers can
connect: point it at `https://<your-sds-host>/mcp` and send an
`Authorization: Bearer sds_xxxxxxxx` header. If your client only supports local
(stdio) servers, use the `mcp-remote` bridge shown under Claude Desktop. Check
your client's own documentation for where its MCP config lives.

---

## Available tools

| Tool | Arguments | What it does |
|------|-----------|--------------|
| `list_resources` | none | List all HPC clusters/resources. |
| `search_software` | `query` | Search software by name, description, research field, or tags. |
| `get_software_details` | `name` | Full details for one package: load commands per resource and containers. |
| `get_software_containers` | `name` | Container images available for a package. |
| `get_resource_software` | `resource` | All software available on a specific cluster. |
| `match_software_to_resources` | `packages`, `fuzzy` | Given a list of packages, which clusters support them (unmatched listed separately). |

These call the SDS REST API under the hood; see `API.md` for the underlying
endpoints and response shapes.

## Example prompts

- "What HPC clusters are available, and what's installed on each?"
- "Which resources have a containerized build of the package I need?"
- "Which clusters support everything in my requirements.txt?"
- "How do I load a given package on a specific cluster?"

---

## Running the server yourself

Most users don't need this; use your institution's hosted endpoint above.
If you're developing against SDS or running your own instance, install it from
the SDS repository and run it against a local SDS app:

```bash
pip install -e ./mcp
SDS_API_URL=http://localhost:8080/api/v1 SDS_API_KEY=sds_xxxxxxxx sds-mcp
```

It reads `SDS_API_URL` (the SDS REST API base) and `SDS_API_KEY`. Point your MCP
client at the resulting process using that client's stdio-server configuration.
