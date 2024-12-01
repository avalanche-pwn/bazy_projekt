import functools
from extensions import pgdb

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route("/login", methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        raise NotImplementedError
    
    return "test"

@bp.route("/register", methods=('GET', ))
def register():
    raise NotImplementedError
