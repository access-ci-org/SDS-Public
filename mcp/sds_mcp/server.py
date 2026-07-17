#!/usr/bin/env python3
import json
import os
from typing import List

from sds_mcp.client import get, post

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "SDS",
    instructions=(
        "You have access to an HPC Software Documentation Service (SDS). "
        "Use list_resources to see available clusters, search_software to find "
        "software by name or research domain, get_software_details to see load "
        "commands and container availability for a specific package, "
        "get_software_containers to list container images for a package, "
        "get_resource_software to list all software on a specific cluster, and "
        "match_software_to_resources to find which clusters support a set of packages."
    ),
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", "9000")),
)


@mcp.tool()
def list_resources() -> str:
    """List all HPC clusters/resources tracked by this SDS instance."""
    data = get("/resources")
    return json.dumps(data, indent=2)


@mcp.tool()
def search_software(query: str) -> str:
    """Search for software by name, description, research field, or tags.

    Returns software names, descriptions, research fields, tags, available
    resources, load commands, and whether a container exists.

    Args:
        query: Search term (e.g. "bioinformatics", "BLAST", "machine learning").
               Leave empty to list up to 100 packages.
    """
    data = get("/software/search", params={"q": query})
    return json.dumps(data, indent=2)


@mcp.tool()
def get_software_details(name: str) -> str:
    """Get full details for a specific software package, including all load
    commands per resource and all available container images.

    Args:
        name: Exact software name as returned by search_software.
    """
    data = get(f"/software/{name}")
    return json.dumps(data, indent=2)


@mcp.tool()
def get_software_containers(name: str) -> str:
    """List all container images available for a specific software package,
    including the container file path, resource, supported versions, and
    any usage notes.

    Args:
        name: Exact software name as returned by search_software.
    """
    data = get(f"/software/{name}/containers")
    return json.dumps(data, indent=2)


@mcp.tool()
def get_resource_software(resource: str) -> str:
    """List all software available on a specific HPC cluster/resource, with
    versions and load commands.

    Args:
        resource: Resource name as returned by list_resources.
    """
    data = get(f"/resources/{resource}/software")
    return json.dumps(data, indent=2)


@mcp.tool()
def match_software_to_resources(packages: List[str], fuzzy: bool = True) -> str:
    """Given a list of package names (e.g. from a requirements.txt or import
    list), return all matching HPC software entries and which resources have
    them. Each package may match multiple catalog entries (e.g. "numpy" matches
    numpy, py-numpy, py3-numpy). Unmatched packages are listed separately.

    Args:
        packages: List of package/import names, e.g. ["torch", "tensorflow", "blast"].
                  At most 500 per call; split longer lists across calls.
        fuzzy: Use fuzzy matching to handle name variations like "torch" -> "PyTorch".
               Defaults to true.
    """
    data = post("/software/match-resources", {"packages": packages, "fuzzy": fuzzy})
    return json.dumps(data, indent=2)


def main():
    # stdio for laptop installs (default); streamable-http when hosted in the
    # container (supervisord sets MCP_TRANSPORT=streamable-http).
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
