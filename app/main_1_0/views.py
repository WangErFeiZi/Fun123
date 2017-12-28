from . import main
from flask import render_template, jsonify
from random import randint


@main.route('/test')
def test():
    # return render_template('index.html', path='test123')
    response = {
        'randomNumber': randint(1, 100)
    }
    return jsonify(response)


