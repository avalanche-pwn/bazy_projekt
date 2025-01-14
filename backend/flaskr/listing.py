from flaskr.extensions import pgdb
from flaskr.form import BaseForm
from flaskr.flash_msg import FlashMsg
from flaskr.auth import required_loggedin
from wtforms import RadioField, IntegerField, DecimalField, SelectField, FieldList, HiddenField, FormField, DateField, TimeField, validators
from flaskr.category_helpers import CatNode, tee_lookahead, cat_tree_builder, CatTree, av_categories, open_chosen_cat, child_categories
from flask import render_template
from flask import current_app as app
from flask import (Blueprint, flash, g, redirect, render_template, request,
                   session, url_for, Response, send_from_directory)
from functools import lru_cache
from itertools import tee
from dataclasses import dataclass
from datetime import datetime, timedelta

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
    rim_or_centerfire = SelectField("Rim/Centerfire",
                                    choices=["rim", "centerfire"])
    weight = IntegerField("Waga (g)")


class ReserveItemForm(BaseForm):
    m_id = HiddenField("m_id", validators = [validators.DataRequired()])
    quantity = IntegerField("Ilość", default=1, validators=[validators.DataRequired()])


class ReserveForm(BaseForm):
    quantities = FieldList(FormField(ReserveItemForm))
    date = DateField("Data")
    time = TimeField("Godzina", validators = [validators.DataRequired()])


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
    quantity: int
    image_file: str
    manufacturer_code: str
    name: str
    model: str
    caliber: float
    price_per_hour: float
    category: str


@dataclass
class Ammunition:
    quantity: int
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
def download_file(name: str) -> Response:
    return send_from_directory(app.config["UPLOAD_DIR"], name)


@bp.route('/reserve/<string:type_>/<m_code>', methods=['GET'])
@required_loggedin
def reserve(type_: str, m_code: str) -> Response:
    if type_ == "gun":
        if session.get("to_reserve_guns") and m_code not in session.get("to_reserve_guns"):
            session["to_reserve_guns"].append(m_code)
        session["to_reserve_guns"] = [m_code]
        flash(FlashMsg("success", "Dodano do rezerwacji"))
    elif type_ == "ammo":
        if session.get("to_reserve_ammo") and m_code not in session.get("to_reserve_ammo"):
            session["to_reserve_ammo"].append(m_code)
        session["to_reserve_ammo"] = [m_code]
        flash(FlashMsg("success", "Dodano do rezerwacji"))
    else:
        flash(FlashMsg("danger", "Coś poszło nie tak"))
    return redirect(request.referrer)

def insert_reservation(form: ReserveForm) -> None:
    if form.validate():
        with pgdb.get_cursor() as cursor:
            date = form.date.data
            time = form.time.data
            t = datetime.combine(date, time)
            end_t = t + timedelta(hours=1)
            cursor.execute("""
            INSERT INTO reservations (start_time, end_time, user_id) VALUES (%s, %s, %s) RETURNING reservation_id
            """, (t, end_t, session["user_id"]))
            r_id = cursor.fetchone()[0]
            selected_items = []
            for item in form.quantities:
                selected_items.append(item.m_id.data)
                cursor.execute("""
                SELECT type, quantity FROM EQUIPMENT
                WHERE manufacturer_code = %s
                """, (item.m_id.data, ))
                type_, total = cursor.fetchone()
                if is_gun(type_):
                    cursor.execute("""
                    SELECT COALESCE(SUM(ri.quantity), 0) FROM reservations
                    JOIN reserved_items ri on ri.reservation_id = reservations.reservation_id
                    WHERE end_time between %s AND %s and ri.manufacturer_code = %s
                    """, (t, end_t, item.m_id.data))
                    sum_ = cursor.fetchone()[0]
                    if item.quantity.data + sum_ > total:
                        raise ValueError("Przekroczono liczbę dostępnego sprzętu")
                else:
                    cursor.execute("""
                    SELECT COALESCE(SUM(ri.quantity), 0) FROM reservations
                    JOIN reserved_items ri on ri.reservation_id = reservations.reservation_id
                    WHERE start_time < %s and ri.manufacturer_code = %s
                    """, (t, item.m_id.data))
                    sum_ = cursor.fetchone()[0]
                    if item.quantity.data + sum_ > total:
                        raise ValueError("Przekroczono liczbę dostępnego sprzętu")
                cursor.execute("""
                INSERT INTO reserved_items (reservation_id, manufacturer_code, quantity) VALUES (
                    %s, %s, %s
                )
                """, (r_id, item.m_id.data, item.quantity.data))
            if len(selected_items) != len(set(selected_items)):
                raise ValueError("Ktoś coś hakuje")


@bp.route('clear', methods=['GET'])
@required_loggedin
def clear() -> Response:
    if session.get("to_reserve_guns"):
        del session["to_reserve_guns"]
    if session.get("to_reserve_ammo"):
        del session["to_reserve_ammo"]
    return "ok", 200

class DelForm(BaseForm):
    pass
@bp.route('/delete/<int:r_id>', methods=['POST'])
@required_loggedin
def delete(r_id: int) -> Response:
    form = DelForm(request.form)
    form.validate()
    with pgdb.get_cursor() as cursor:
        cursor.execute("""
        DELETE FROM reservations WHERE user_id = %s AND reservation_id = %s
        """, (session.get("user_id"), r_id))
    return redirect(request.referrer)
    

@bp.route('/reservation', methods=['GET', 'POST'])
@required_loggedin
def reservation() -> Response:
    gun_ids = session.get("to_reserve_guns", [])
    ammo_ids = session.get("to_reserve_ammo", [])
    form = ReserveForm(request.form)
    if request.method == "POST":
        try:
            insert_reservation(form)
            clear()
            flash(FlashMsg("success", "Zarezerwowano"))
            return redirect(url_for("listing.filter"))
        except ValueError as e:
            flash(FlashMsg("danger", e.args[0]))

    guns = []
    ammunition = []
    guns_placeholder = ', '.join('%s' for _ in gun_ids)
    ammo_placeholder = ', '.join('%s' for _ in ammo_ids)
    query_guns = f"""
        SELECT equipment.quantity, equipment.image_file, equipment.manufacturer_code, equipment.name, equipment.model, equipment.caliber, guns.price_per_hour, categories.name AS category_name
        FROM equipment
        JOIN categories ON equipment.type = categories.cat_id
        JOIN guns ON guns.manufacturer_code = equipment.manufacturer_code
        WHERE equipment.manufacturer_code in ({guns_placeholder})
        """
    query_ammo = f"""
        SELECT equipment.quantity, equipment.image_file, equipment.manufacturer_code, equipment.name, equipment.model, equipment.caliber, ammunition.rim_or_centerfire, ammunition.weight, ammunition.price_per_round, categories.name AS category_name
        FROM equipment
        JOIN categories ON equipment.type = categories.cat_id
        JOIN ammunition ON ammunition.manufacturer_code = equipment.manufacturer_code
        WHERE equipment.manufacturer_code in ({ammo_placeholder})
    """
    with pgdb.get_con_cursor() as (con, cursor):
        if gun_ids:
            cursor.execute(query_guns, gun_ids)
            guns = [Gun(*row) for row in cursor.fetchall()]
            for gun in guns:
                form.quantities.append_entry()
        if ammo_ids:
            cursor.execute(query_ammo, ammo_ids)
            ammunition = [Ammunition(*row) for row in cursor.fetchall()]
            for ammo in ammunition:
                form.quantities.append_entry()
    return render_template("listings/reservation.html",
                           ammunition=ammunition,
                           form=form,
                           guns=guns)


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
            SELECT equipment.quantity, equipment.image_file, equipment.manufacturer_code, equipment.name, equipment.model, equipment.caliber, guns.price_per_hour, categories.name AS category_name
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
            SELECT equipment.quantity, equipment.image_file, equipment.manufacturer_code, equipment.name, equipment.model, equipment.caliber, ammunition.rim_or_centerfire, ammunition.weight, ammunition.price_per_round, categories.name AS category_name
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
    return render_template('listings/filter.html',
                           guns=guns,
                           ammunition=ammunition,
                           tree=cat_tree,
                           cat_form=form,
                           current_page=page,
                           params=request.args.to_dict())
