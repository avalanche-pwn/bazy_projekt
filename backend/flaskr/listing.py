from flaskr.extensions import pgdb
from flaskr.form import BaseForm
from wtforms import RadioField, IntegerField, DecimalField, SelectField
from flaskr.category_helpers import CatNode, tee_lookahead, cat_tree_builder, CatTree, av_categories, open_chosen_cat, child_categories
from flask import render_template
from flask import current_app as app
from flask import (Blueprint, flash, g, redirect, render_template, request,
                   session, url_for, Response, send_from_directory)
from functools import lru_cache
from itertools import tee
from dataclasses import dataclass

bp = Blueprint("listing", __name__, url_prefix="/")


@lru_cache(maxsize=1)
def gun_cat_id() -> int:
    with pgdb.get_cursor() as cursor:
        cursor.execute("""
            select cat_id from categories
            where name = 'Broń'
        """)
        return cursor.fetchone()[0]


class FilterForm(BaseForm):
    categories = RadioField("Kategorie", coerce=int, default=gun_cat_id())
    caliber = DecimalField("Kaliber (mm)")
    rim_or_centerfire = SelectField("Rim/Centerfire", choices=["rim", "centerfire"])
    weight = IntegerField("Waga (g)")


@lru_cache(maxsize=128)
def is_gun(cat_id: int) -> bool:
    with pgdb.get_cursor() as cursor:
        cursor.execute(
            """
            with recursive is_gun(cat_id, name, parent_cat_id) as (
                select cat_id, name, parent_cat_id
                from categories
                where cat_id=%s
                union
                select c.cat_id, c.name, c.parent_cat_id 
                from categories c, is_gun
                where c.cat_id = is_gun.parent_cat_id
            )
            select * from is_gun
            where name = 'Broń'
        """, (cat_id, ))
        if cursor.fetchall():
            return True
        return False


def is_ammo(cat_id: int) -> bool:
    return not is_gun(cat_id)


@dataclass
class Gun:
    image_file: str
    manufacturer_code: str
    name: str
    model: str
    caliber: float
    price_per_hour: float
    category: str

@dataclass
class Ammunition:
    image_file: str
    manufacturer_code: str
    name: str
    model: str
    caliber: float
    rim_or_centerfire: str
    weight: int
    price_per_round: float
    category: str


@bp.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config["UPLOAD_DIR"], name)


@bp.route('/', methods=['GET'], defaults={"page": 1})
@bp.route('/<int:page>', methods=['GET'])
def filter(page: int = 1) -> Response:
    if page <= 0:
        page = 1
    cats1, cats2 = tee(av_categories(), 2)
    form = FilterForm(request.args)
    form.categories.choices = [[elem.cat_id, elem.name] for elem in cats1]


    params = []
    form.validate()

    where_clause = ""
    cat_tree = cat_tree_builder(cats2)
    if cat := form.categories.data:
        child_cats = child_categories(cat)
        where_clause += f" AND equipment.type IN ({','.join(('%s' for _ in child_cats))})"
        params += child_cats
        open_chosen_cat(cat_tree, form.categories.data)
        form.categories.default = form.categories.data

    if caliber := form.caliber.data:
        where_clause += " AND equipment.caliber = %s"
        params.append(caliber)


    guns = []
    ammunition = []
    if is_gun(cat):
        query = """
            SELECT equipment.image_file, equipment.manufacturer_code, equipment.name, equipment.model, equipment.caliber, guns.price_per_hour, categories.name AS category_name
            FROM equipment
            JOIN categories ON equipment.type = categories.cat_id
            JOIN guns ON guns.manufacturer_code = equipment.manufacturer_code
            WHERE 1=1
            {where_clause}
            ORDER BY equipment.manufacturer_code
            LIMIT %s OFFSET %s
            """
        with pgdb.get_con_cursor() as (con, cursor):
            cursor.execute(
                query.format(where_clause=where_clause),
                tuple(params) + (app.config["PAGE_SIZE"],
                                 (page - 1) * app.config["PAGE_SIZE"]))
            guns = [Gun(*row) for row in cursor.fetchall()]
    else:
        if rc := form.rim_or_centerfire.data:
            where_clause += " AND ammunition.rim_or_centerfire = %s"
            params.append(rc)

        if weight := form.weight.data:
            where_clause += " AND ammunition.weight = %s"
            params.append(weight)
        query = """
            SELECT equipment.image_file, equipment.manufacturer_code, equipment.name, equipment.model, equipment.caliber, ammunition.rim_or_centerfire, ammunition.weight, ammunition.price_per_round, categories.name AS category_name
            FROM equipment
            JOIN categories ON equipment.type = categories.cat_id
            JOIN ammunition ON ammunition.manufacturer_code = equipment.manufacturer_code
            WHERE 1=1
            {where_clause}
            ORDER BY equipment.manufacturer_code
            LIMIT %s OFFSET %s
        """
        with pgdb.get_con_cursor() as (con, cursor):
            cursor.execute(
                query.format(where_clause=where_clause),
                tuple(params) + (app.config["PAGE_SIZE"],
                                 (page - 1) * app.config["PAGE_SIZE"]))
            ammunition = [Ammunition(*row) for row in cursor.fetchall()]


    # Pobierz kategorie do menu bocznego

    # Renderuj widok
    return render_template(
        'listings/filter.html',
        guns=guns,
        ammunition=ammunition,
        tree=cat_tree,
        cat_form=form,
        current_page=page,
        params=request.args.to_dict()
    )
