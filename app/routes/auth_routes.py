from urllib.parse import urljoin, urlparse

from flask import request, redirect, flash, url_for, render_template
from flask_login import login_user, logout_user, login_required, current_user
from peewee import DoesNotExist
from app.models.users import Users
from app.logic.sdsVersions import get_pending_updates, PRIORITY_TO_ALERT
from . import auth_bp


def _is_safe_url(target: str) -> bool:
    """Only allow redirects to URLs on this same host."""
    if not target:
        return False
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ("http", "https") and ref.netloc == test.netloc


def _safe_next() -> str | None:
    nxt = request.args.get("next")
    return nxt if _is_safe_url(nxt) else None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_safe_next() or url_for("software.software_search"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username and password are required", "danger")
            return redirect(url_for("auth.login"))

        try:
            user = Users.get(Users.username == username)
            if user and user.check_password(password=password):
                login_user(user)
                updates = get_pending_updates()
                if updates:
                  for update in updates:
                      flash(
                        update["alert_message"],
                        update["alert_type"]
                      )
                return redirect(_safe_next() or url_for("software.software_search"))
            flash("Invalid username and password", "danger")
        except DoesNotExist:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    logout_user()
    flash("Successfully logged out", "success")
    return redirect(url_for("software.software_search"))
