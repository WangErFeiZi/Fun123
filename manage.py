#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from random import randint

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')

from app import create_app, db
from app.models import Permission, User, Role, Follow, Actor, Movie, TV, Novel, Uploader
from flask import render_template, request, jsonify
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

app = create_app(os.getenv('FLASKY_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app)


def make_shell_context():
    return dict(app=app, db=db,
                Permission=Permission, User=User, Role=Role, Follow=Follow,
                Actor=Actor, Movie=Movie, TV=TV, Novel=Novel, Uploader=Uploader)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def test(coverage=False):
    '''
    启动单元测试
    '''

    if coverage and not os.environ.get('FLASKY_COVERAGE'):
        import sys
        os.environ['FLASKY_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)

    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

    if COV:
        COV.stop()
        COV.save()
        print('单元测试覆盖报告')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML版本: file://{}/index.html'.format(covdir))
        COV.erase()


@manager.command
def profile(length=25, profile_dir=None):
    '''
    在性能分析器监视下启动服务器
    '''
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app,
                                      restrictions=[length], profile_dir=profile_dir)
    app.run()


@manager.command
def deploy():
    '''
    启动部署任务
    '''
    from flask_migrate import upgrade
    from app.models import User, Role
    upgrade()
    Role.insert_roles()
    User.add_self_follows()


@manager.command
def drop_db():
    '''
    清空数据库
    '''
    db.drop_all()


if __name__ == '__main__':
    manager.run()