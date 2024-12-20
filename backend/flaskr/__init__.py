import os

from flask import Flask
from flaskr import auth, settings
from flaskr.extensions import pgdb
from flask_wtf import CSRFProtect 


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    pgdb.init_app(app)
    CSRFProtect(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(settings.bp)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    return app
