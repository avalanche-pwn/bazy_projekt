import os

from flask import Flask
from flaskr import auth, settings, admin, reservations  # Dodajemy import blueprintu reservations
from flaskr.extensions import pgdb
from flask_wtf import CSRFProtect

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
        UPLOAD_DIR="/uploads",
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    app.jinja_env.filters['zip'] = zip
    app.jinja_env.add_extension('jinja2.ext.loopcontrols')

    pgdb.init_app(app)
    CSRFProtect(app)

    # Rejestrujemy blueprinty
    app.register_blueprint(auth.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(reservations.bp)  # Rejestracja blueprintu reservations

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    return app
