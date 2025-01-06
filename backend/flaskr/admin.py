from flaskr.extensions import pgdb
from flaskr.flash_msg import FlashMsg
from flask import current_app as app
import psycopg2
from wtforms import StringField, PasswordField, validators, IntegerField, HiddenField, RadioField, FileField
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


class AddType(BaseForm):
    name = StringField("Wyświetlana nazwa",
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
    caliber = IntegerField(
        "Kaliber",
        [validators.DataRequired()],
    )
    image = FileField("Zdjęcie")
    parent_category = HiddenField(id="parent_cat",
                                  validators=[validators.DataRequired()])


class AddCategory(BaseForm):
    av_categories = RadioField("Kategoria", coerce=int)
    new_cat = StringField("Nazwa kategorii",
                          validators=[
                              validators.DataRequired(),
                          ])


@dataclass
class CatNode:
    depth: int
    cat_id: int
    name: str
    show: bool = field(default=False)


T = TypeVar("T")


def tee_lookahead(tee_iterator: Iterator[T], default: T) -> T:
    fork, = tee(tee_iterator, 1)
    return next(fork, default)


CatTree = list[Union[CatNode, 'CatTree']]


def cat_tree_builder(it: Iterator[CatNode],
                     children: CatTree | None = None,
                     depth: int = 0) -> CatTree:
    if not children:
        children = []

    if tee_lookahead(it, CatNode(-1, -1, "placeholder")).depth < depth:
        return children

    for node in it:
        if node.depth == depth:
            children.append(node)
        elif node.depth > depth:
            children.append(cat_tree_builder(it, [node], depth + 1))

        if tee_lookahead(it, CatNode(-1, -1, "placeholder")).depth < depth:
            return children

    return children


def av_categories() -> Iterator[CatNode]:
    with pgdb.get_cursor() as cursor:
        cursor.execute("""
with recursive cat_hierarchy(cat_id, name, parent_cat_id, depth, path) as (
	SELECT cat_id, name, parent_cat_id, 0 as depth, ARRAY[cat_id] from categories where parent_cat_id is null
	union 
	select c.cat_id, c.name, c.parent_cat_id, cat_hierarchy.depth + 1, path || c.cat_id from categories c, cat_hierarchy
	where c.parent_cat_id = cat_hierarchy.cat_id
)
select depth, cat_id, name from cat_hierarchy
order by path
                """)
        [iterator] = tee((CatNode(*row) for row in cursor.fetchall()), 1)
        return iterator


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


def open_chosen_cat(tree: CatTree, chosen: int) -> bool:
    assert isinstance(tree, list)

    parent = CatNode(-1, -1, "placeholder", False)
    for child in tree:
        if isinstance(child, list):
            if open_chosen_cat(child, chosen):
                parent.show = True
                return True
        else:
            if child.cat_id == chosen:
                parent.show = True
                child.show = True
                return True
            parent = child
    return False


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
        if not form.validate():
            flash(FlashMsg("danger", "Nieprawidłowe dane w formularzu"))
            errors = True

        if "image" in request.files:
            file = request.files["image"]
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
            with pgdb.get_cursor() as cursor:
                try:
                    cursor.execute(
                        """
                    INSERT INTO equipment (manufacturer_code, image_file, name, model, quantity, caliber, type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (form.model.data, filename, form.name.data, form.model.data,
                          form.quantity.data, form.caliber.data,
                          form.parent_category.data))
                    flash(FlashMsg("success", "Dodano"))
                except psycopg2.errors.UniqueViolation:
                    flash(FlashMsg("danger", "Model o takim kodzie producent już jest dodany"))

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
