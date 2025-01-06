from flask import render_template


@bp.route('/filter', methods=['GET'])
def filter():
    # Pobierz parametry GET
    category_id = request.args.get('category', None)
    caliber = request.args.get('caliber', None)
    price_min = request.args.get('price_min', None, type=float)
    price_max = request.args.get('price_max', None, type=float)

    # Zapytanie do bazy danych
    query = """
        SELECT equipment.manufacturer_code, equipment.name, equipment.model, equipment.price_per_hour, categories.name AS category_name
        FROM equipment
        JOIN categories ON equipment.type = categories.cat_id
        WHERE 1=1
    """

    params = []

    if category_id:
        query += " AND equipment.type = %s"
        params.append(category_id)

    if caliber:
        query += " AND equipment.caliber = %s"
        params.append(caliber)

    if price_min is not None:
        query += " AND equipment.price_per_hour >= %s"
        params.append(price_min)

    if price_max is not None:
        query += " AND equipment.price_per_hour <= %s"
        params.append(price_max)

    # Wykonaj zapytanie
    with pgdb.get_con_cursor() as (con, cursor):
        cursor.execute(query, tuple(params))
        items = cursor.fetchall()

    # Pobierz kategorie do menu bocznego
    with pgdb.get_con_cursor() as (con, cursor):
        cursor.execute("SELECT cat_id, name FROM categories")
        categories = cursor.fetchall()

    # Renderuj widok
    return render_template('reservations/filter.html', items=items, categories=categories)
