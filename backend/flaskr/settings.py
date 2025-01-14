import functools
from flaskr.extensions import pgdb
from flaskr.flash_msg import FlashMsg
from flaskr.listing import DelForm
import bcrypt
import psycopg2
from wtforms import StringField, PasswordField, validators
from flaskr.form import BaseForm
from flaskr.auth import required_loggedin, fetch_user
from flaskr.models import User
from dataclasses import dataclass
from werkzeug.datastructures import MultiDict

from flask import (
    Response,
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
    name = StringField("Imię",
                       [validators.DataRequired(),
                        validators.Length(max=50)])
    surname = StringField(
        "Nazwisko",
        [validators.DataRequired(),
         validators.Length(max=50)],
    )
    email = StringField(
        "E-mail",
        [validators.DataRequired(),
         validators.Length(min=10, max=100)],
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
    confirm = PasswordField("Powtórz hasło",
                            [validators.Length(min=10, max=72)])


class DeleteForm(BaseForm):
    pass


@bp.route("/edit_data", methods=("POST", ))
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


@bp.route("/edit_passwd", methods=("POST", ))
@required_loggedin
def edit_password():
    form = EditPasswordForm(request.form)
    session["pwd_form"] = request.form
    if form.validate():
        with pgdb.get_cursor() as cursor:
            cursor.execute(
                "UPDATE users SET pwd_salty=%s WHERE user_id=%s",
                (
                    bcrypt.hashpw(form.password.data.encode(),
                                  bcrypt.gensalt()).decode(),
                    session["user_id"],
                ),
            )
            flash(FlashMsg("success", "Zmieniono hasło"))
    return redirect(url_for("settings.settings"))


@bp.route("/delete", methods=("POST", ))
@required_loggedin
def delete():
    delete_form = DeleteForm(request.form)
    if not delete_form.validate():
        flash("danger", "Błędny token CSRF")
        return redirect(url_for("auth.settings"))

    with pgdb.get_cursor() as cursor:
        cursor.execute("DELETE FROM users WHERE user_id = %s",
                       (session["user_id"], ))
        session.clear()
        flash(FlashMsg("danger", "Usunięto konto"))
        return redirect(url_for("auth.login"))


@bp.route("/", methods=("GET", ))
@required_loggedin
def settings() -> Response:
    edit_form = EditDataForm(request.form)
    reserve_del_form = DeleteForm(request.form)
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
    with pgdb.get_cursor() as cursor:
        cursor.execute(
            "SELECT reservation_id, start_time FROM reservations WHERE user_id = %s",
            (session.get("user_id"), ))
        reservations = cursor.fetchall()

    return render_template("auth/settings.html",
                           delete_form=delete_form,
                           edit_form=edit_form,
                           pwd_form=pwd_form,
                           user=fetch_user(session["user_id"]),
                           reservations=reservations,
                           reserve_del_form=reserve_del_form)
