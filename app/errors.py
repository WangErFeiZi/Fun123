from flask import current_app, jsonify


class ValidationError(ValueError):
    pass


def bad_request(message):
    resp = jsonify({'error': 'bad request', message: message})
    resp.status_code = 400
    return resp


def unauthorized(message):
    resp = jsonify({'error': 'unauthorized', message: message})
    resp.status_code = 401
    return resp


def forbidden(message):
    resp = jsonify({'error': 'forbidden', message: message})
    resp.status_code = 403
    return resp
