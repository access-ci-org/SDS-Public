from flask import request, redirect, flash, url_for, render_template
from flask_login import login_user, logout_user, login_required, current_user
from peewee import DoesNotExist
from app.models.users import Users
from . import auth_bp


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        next_page = request.args.get("next")
        return redirect(next_page if next_page else url_for("software.software_search"))
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
                next_page = request.args.get("next")
                return redirect(
                    next_page if next_page else url_for("software.software_search")
                )
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
