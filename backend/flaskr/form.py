from flask_wtf import FlaskForm
from flask import session

class BaseForm(FlaskForm):
    class Meta:
        locales = ["pl_PL"]
