import functools
from flaskr.extensions import pgdb
from flaskr.flash_msg import FlashMsg
import bcrypt
import psycopg2
from wtforms import StringField, PasswordField, validators
from flaskr.form import BaseForm

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

bp = Blueprint("auth", __name__, url_prefix="/auth")


def redirect_loggedin(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_id"):
            return redirect("/")

        return view(**kwargs)

    return wrapped_view


class RegisterForm(BaseForm):
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
    password = PasswordField(
        "Hasło", [validators.DataRequired(), validators.Length(min=10, max=72)]
    )
    confirm = PasswordField(
        "Powtórz hasło", [validators.Length(min=10, max=72)]
    )


class LoginForm(BaseForm):
    email = StringField(
        "E-mail",
        [validators.DataRequired()],
    )
    password = PasswordField("Powtórz hasło", [validators.DataRequired()])


@bp.route("/login", methods=("GET", "POST"))
@redirect_loggedin
def login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():

        with pgdb.get_cursor() as cursor:
            cursor.execute(
                "SELECT user_id, pwd_salty, is_admin FROM users WHERE email = %s",
                (form.email.data,),
            )

            res = cursor.fetchall()
            if res and bcrypt.checkpw(
                form.password.data.encode(), res[0][1].encode()
            ):
                session["user_id"] = res[0][0]
                session["is_admin"] = res[0][2]
                return redirect("/")

            flash(FlashMsg("danger", "Błędny email lub hasło"))

    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=("GET", "POST"))
@redirect_loggedin
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        with pgdb.get_cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO users (name, surname, email, pwd_salty) VALUES (%s, %s, %s, %s)",
                    (
                        form.name.data,
                        form.surname.data,
                        form.email.data,
                        bcrypt.hashpw(
                            form.password.data.encode("utf-8"),
                            bcrypt.gensalt(),
                        ).decode(),
                    ),
                )
                flash(
                    FlashMsg("primary", "Zarejestrowano, możesz się zalogować")
                )
            except psycopg2.errors.UniqueViolation:
                flash(
                    FlashMsg(
                        "warning", "Użytkownik o podanym e-mail już istnieje"
                    )
                )
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/logout", methods=("GET",))
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
