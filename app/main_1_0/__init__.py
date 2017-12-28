from flask import Blueprint

main = Blueprint('main', __name__)

# from . import authentication, posts, users,comments, errors
from . import views
