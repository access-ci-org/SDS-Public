from flask import render_template, request, jsonify, redirect, url_for
from app import app
from app.models.resource import Resource
from app.logic.containers import get_all_containers, get_container_info

from . import container_bp


@container_bp.route("/containers", methods=["POST", "GET"])
def search_container():
    if not app.config["SHOW_CONTAINER_PAGE"]:
        return redirect(url_for("software.software_search"))
    resources = [resource.resource_name for resource in Resource.select()]
    container_data = get_all_containers()
    return render_template("container_search.html", resources=resources, container_data=container_data)


@container_bp.route("/container_details", methods=["POST"])
def container_details():
    data = request.get_json(silent=True) or {}
    container_name = data.get("containerName")
    resource_name = data.get("resourceName")

    if not (container_name and resource_name):
        return jsonify({"error": "Missing required fields"}), 400

    container_info = get_container_info(container_name, resource_name)
    if not container_info:
        return jsonify({"error": "Container not found"}), 404
    return container_info
