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
    data = request.get_json()

    container_info = get_container_info(
        data.get("containerName"), data.get("resourceName")
    )
    if container_info:
        return container_info
    else:
        return jsonify({"error": "Missing column name"}), 400
