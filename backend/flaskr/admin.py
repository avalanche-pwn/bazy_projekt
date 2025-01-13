from flaskr.extensions import pgdb
from flaskr.flash_msg import FlashMsg
from flaskr.category_helpers import CatNode, tee_lookahead, cat_tree_builder, CatTree, av_categories, open_chosen_cat
from flask import current_app as app
import psycopg2
from wtforms import StringField, PasswordField, validators, IntegerField, HiddenField, RadioField, FileField, SelectField, DecimalField, FormField, SubmitField
from flaskr.form import BaseForm
from flaskr.auth import required_loggedin, fetch_user, required_admin
from flaskr.models import User
from dataclasses import dataclass, field
from werkzeug.datastructures import MultiDict
from werkzeug.utils import secure_filename
from typing import Generator, Sequence, TypeVar, Iterator, Union
from itertools import tee
from uuid import uuid4
import os

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Response,
)

bp = Blueprint("admin", __name__, url_prefix="/administration")


class AmmoForm(BaseForm):
    rim_or_centerfire = SelectField("Rodzaj",
                                    choices=["rim", "centerfire"],
                                    validators=[validators.DataRequired()])
    weight = IntegerField("Waga", validators=[validators.DataRequired()])
    price = DecimalField("Cena za sztukę",
                         validators=[validators.DataRequired()])
    submit = SubmitField("Dodaj")


class GunForm(BaseForm):
    price = DecimalField("Cena za godzinę",
                         validators=[validators.DataRequired()])
    submit = SubmitField("Dodaj")


class AddTypeMain(BaseForm):
    gun_name = StringField(
        "Wyświetlana nazwa",
        [validators.DataRequired(),
         validators.Length(max=50)])
    model = StringField(
        "Model",
        [validators.DataRequired(),
         validators.Length(max=50)],
    )
    quantity = IntegerField(
        "Dostępna ilość",
        [validators.DataRequired()],
    )
    caliber = DecimalField(
        "Kaliber",
        [validators.DataRequired()],
    )
    image = FileField("Zdjęcie")
    parent_category = HiddenField(id="parent_cat",
                                  validators=[validators.DataRequired()])


class AddType(BaseForm):
    common = FormField(AddTypeMain)
    ammo = FormField(AmmoForm)
    gun = FormField(GunForm)


class AddCategory(BaseForm):
    av_categories = RadioField("Kategoria", coerce=int)
    new_cat = StringField("Nazwa kategorii",
                          validators=[
                              validators.DataRequired(),
                          ])


@bp.route("/add_cat", methods=("POST", ))
@required_admin
def add_cat() -> Response:
    cat_form = AddCategory(request.form)
    cat_form.av_categories.choices = [[elem.cat_id, elem.name]
                                      for elem in av_categories()]
    if not cat_form.validate():
        return "error", 403

    with pgdb.get_cursor() as cursor:
        cursor.execute(
            "INSERT INTO categories (name, parent_cat_id) values (%s, %s) RETURNING cat_id",
            (cat_form.new_cat.data, cat_form.av_categories.data))
        cat_id = cursor.fetchone()

    return redirect(url_for("admin.index", cat=cat_id))


def insert_equipment(form: AddType, filename: str) -> None:
    with pgdb.get_con_cursor() as (con, cursor):
        try:
            cursor.execute(
                """
            INSERT INTO equipment (manufacturer_code, image_file, name, model, quantity, caliber, type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (form.common.model.data, filename, form.common.gun_name.data,
                  form.common.model.data, form.common.quantity.data,
                  form.common.caliber.data, form.common.parent_category.data))

            if form.gun.submit.data and form.gun.validate(form):
                cursor.execute(
                    """
                INSERT INTO guns (manufacturer_code, price_per_hour) VALUES (%s, %s)
                """, (form.common.model.data, form.gun.price.data))
            elif form.ammo.submit.data and form.ammo.validate(form):
                cursor.execute(
                    """
                INSERT INTO ammunition (manufacturer_code, rim_or_centerfire, weight, price_per_round)
                VALUES (%s, %s, %s, %s)
                """, (form.common.model.data, form.ammo.rim_or_centerfire.data,
                      form.ammo.weight.data, form.ammo.price.data))
            else:
                con.rollback()
                flash(FlashMsg("warning", "Nieprawidłowe dane w formularzu"))
                return

            flash(FlashMsg("success", "Dodano"))
        except psycopg2.errors.UniqueViolation:
            flash(
                FlashMsg("danger",
                         "Model o takim kodzie producent już jest dodany"))


@bp.route("/", methods=("GET", "POST"))
@required_admin
def index() -> Response:
    param = request.args.get("cat")
    chosen = param
    if param is not None:
        try:
            chosen = int(param)
        except TypeError:
            chosen = 1

    form = AddType(request.form)
    cat_form = AddCategory(request.form)

    errors = False
    if request.method == "POST":
        if not form.common.validate(form):
            flash(FlashMsg("danger", "Nieprawidłowe dane w formularzu"))
            errors = True

        if "common-image" in request.files:
            file = request.files["common-image"]
            extension = secure_filename(file.filename.split(".")[-1]).lower()
            filename = uuid4().hex + "." + extension
            if extension in ["jpg", "png"]:
                file.save(os.path.join(app.config["UPLOAD_DIR"], filename))
            else:
                flash(FlashMsg("danger", "Nieprawidłowe rozszerzenie pliku"))
                errors = True
        else:
            flash(FlashMsg("warning", "Brak wstawianego pliku"))
            errors = True

        if not errors:
            insert_equipment(form, filename)

    cats1, cats2 = tee(av_categories(), 2)
    cat_tree = cat_tree_builder(cats1)
    open_chosen_cat(cat_tree, chosen)

    cat_form.av_categories.choices = [[elem.cat_id, elem.name]
                                      for elem in cats2]
    cat_form.av_categories.default = chosen
    cat_form.process()
    return render_template("admin/index.html",
                           add_type_form=form,
                           cats=cat_form,
                           tree=cat_tree,
                           cat=chosen)
