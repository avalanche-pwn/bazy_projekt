import functools
from flaskr.extensions import pgdb
from flaskr.flash_msg import FlashMsg
import bcrypt
import psycopg2

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
            return redirect('/')

        return view(**kwargs)

    return wrapped_view


@bp.route("/login", methods=("GET", "POST"))
@redirect_loggedin
def login():
    if request.method == "POST":
        email = request.form["email"]

        with pgdb.get_cursor() as cursor:
            cursor.execute(
                "SELECT user_id, pwd_salty, is_admin FROM users WHERE email = %s",
                (email, ),
            )
            
            res = cursor.fetchall()
            if not res:
                flash(FlashMsg("danger", "Użytkownik nie istnieje"))
                return render_template("auth/login.html")

            if bcrypt.checkpw(request.form["password"].encode(), res[0][1].encode()):
                session["user_id"] = res[0][0]
                session["is_admin"] = res[0][2]
                return redirect("/")

            flash(FlashMsg("Danger", "Błędne hasło"))
        
    return render_template("auth/login.html")


@bp.route("/register", methods=("GET", "POST"))
@redirect_loggedin
def register():
    if request.method == "POST":
        error = None
        if not request.form["name"]:
            error = "Imię jest wymagane"

        elif not request.form["surname"]:
            error = "Nazwisko jest wymagane"

        elif not request.form["email"]:
            error = "E-mail jest wymagany"

        elif not request.form["password"]:
            error = "Hasło jest wymagane"
        elif request.form["password"] != request.form["password_repeat"]:
            error = "Hasła się nie zgadzają"

        if error:
            flash(FlashMsg("danger", error))
            return render_template("auth/register.html")

        with pgdb.get_cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO users (name, surname, email, pwd_salty) VALUES (%s, %s, %s, %s)",
                    (
                        request.form["name"],
                        request.form["surname"],
                        request.form["email"],
                        bcrypt.hashpw(
                            request.form["password"].encode("utf-8"),
                            bcrypt.gensalt(),
                        ).decode(),
                    ),
                )
                flash(FlashMsg("primary", "Zarejestrowano, możesz się zalogować"))
            except psycopg2.errors.UniqueViolation:
                flash(FlashMsg("warning", "Użytkownik o podanym e-mail już istnieje"))
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html")

@bp.route("/logout", methods=("GET", ))
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
