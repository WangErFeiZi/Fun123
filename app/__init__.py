from flask import Flask, render_template
from flask_cors import CORS
from flask_login import LoginManager
from flask_mail import Mail
from flask_pagedown import PageDown
from flask_sqlalchemy import SQLAlchemy
from config import config

mail = Mail()
pagedown = PageDown()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth_api_1_0.login'


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    pagedown.init_app(app)
    mail.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    CORS(app)

    if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
        from flask_sslify import SSLify
        sslify = SSLify(app)

    from .auth_1_0 import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/api/auth/v1.0')
    from .main_1_0 import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/api/main/v1.0')
    from .module_1_0 import module as module_blueprint
    app.register_blueprint(module_blueprint, url_prefix='/api/module/v1.0')

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        '''
        @user.route('/<user_id>', defaults={'username': None})
        @user.route('/<user_id>/<username>')
        类似于这种用法，除蓝图中的API接口外，其它所以URL全部返回index.html，并把path传给前端。
        '''
        # if app.debug:
        #     return requests.get('http://localhost:5000/{}'.format(path)).text
        return render_template('index.html', path=path)

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    from.errors import ValidationError, bad_request

    @app.errorhandler(ValidationError)
    def validation_error(e):
        return bad_request(e.args[0])

    return app


