import functools
from flaskr.extensions import pgdb
from flaskr.flash_msg import FlashMsg
import bcrypt
import psycopg2
from wtforms import StringField, PasswordField, validators
from flaskr.form import BaseForm
from flaskr.auth import required_loggedin, fetch_user
from flaskr.models import User
from dataclasses import dataclass
from werkzeug.datastructures import MultiDict

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

bp = Blueprint("settings", __name__, url_prefix="/settings")


class EditDataForm(BaseForm):
    name = StringField(
        "Imię", [validators.DataRequired(), validators.Length(max=50)]
    )
    surname = StringField(
        "Nazwisko",
        [validators.DataRequired(), validators.Length(max=50)],
    )
    email = StringField(
        "E-mail",
        [validators.DataRequired(), validators.Length(min=10, max=100)],
    )


class EditPasswordForm(BaseForm):
    password = PasswordField(
        "Hasło",
        [
            validators.DataRequired(),
            validators.Length(min=10, max=72),
            validators.EqualTo("confirm", message="Hasła się nie zgadzają"),
        ],
    )
    confirm = PasswordField(
        "Powtórz hasło", [validators.Length(min=10, max=72)]
    )


class DeleteForm(BaseForm):
    pass


@bp.route("/edit_data", methods=("POST",))
@required_loggedin
def edit():
    form = EditDataForm(request.form)
    g.edit_form = request.form
    if form.validate():
        with pgdb.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET name=%s, surname=%s, email=%s WHERE user_id=%s",
                (
                    form.name.data,
                    form.surname.data,
                    form.email.data,
                    session["user_id"],
                ),
            )
            flash(FlashMsg("success", "Zaktualizowano dane"))
    return redirect(url_for("settings.settings"))


@bp.route("/edit_passwd", methods=("POST",))
@required_loggedin
def edit_password():
    form = EditPasswordForm(request.form)
    session["pwd_form"] = request.form
    if form.validate():
        with pgdb.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET pwd_salty=%s WHERE user_id=%s",
                (
                    bcrypt.hashpw(
                        form.password.data.encode(), bcrypt.gensalt()
                    ).decode(),
                    session["user_id"],
                ),
            )
            flash(FlashMsg("success", "Zmieniono hasło"))
    return redirect(url_for("settings.settings"))


@bp.route("/delete", methods=("POST",))
@required_loggedin
def delete():
    delete_form = DeleteForm(request.form)
    if not delete_form.validate():
        flash("danger", "Błędny token CSRF")
        return redirect(url_for("auth.settings"))

    with pgdb.get_cursor() as cursor:
        cursor.execute(
            "DELETE FROM users WHERE user_id = %s", (session["user_id"],)
        )
        session.clear()
        flash(FlashMsg("danger", "Usunięto konto"))
        return redirect(url_for("auth.login"))


@bp.route("/", methods=("GET",))
@required_loggedin
def settings():
    print(request.args)
    edit_form = EditDataForm(request.form)
    if form := session.get("edit_form"):
        edit_form = EditDataForm(MultiDict(form))
        session.pop("edit_form")
        edit_form.validate()
    pwd_form = EditPasswordForm(request.form)
    if form := session.get("pwd_form"):
        pwd_form = EditPasswordForm(MultiDict(form))
        session.pop("pwd_form")
        pwd_form.validate()
    delete_form = DeleteForm(request.form)

    return render_template(
        "auth/settings.html",
        delete_form=delete_form,
        edit_form=edit_form,
        pwd_form=pwd_form,
        user=fetch_user(session["user_id"]),
    )

@bp.route("/view_guns", methods=("GET",))
@required_loggedin
def view_guns():
    """Wyświetla listę broni z podziałem na kategorie."""
    with pgdb.get_cursor() as cursor:
        cursor.execute(
            """
            SELECT e.name, e.model, e.caliber, g.price_per_hour
            FROM equipment e
            JOIN guns g ON e.manufacturer_code = g.manufacturer_code
            """
        )
        guns = cursor.fetchall()

    return render_template("view_guns.html", guns=guns)


@bp.route("/view_ammunition", methods=("GET",))
@required_loggedin
def view_ammunition():
    """Wyświetla listę amunicji z podziałem na kategorie."""
    with pgdb.get_cursor() as cursor:
        cursor.execute(
            """
            SELECT e.name, e.model, e.caliber, a.rim_or_centerfire, a.weight, a.price_per_round
            FROM equipment e
            JOIN ammunition a ON e.manufacturer_code = a.manufacturer_code
            """
        )
        ammunition = cursor.fetchall()

    return render_template("view_ammunition.html", ammunition=ammunition)
