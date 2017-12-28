import hashlib, bleach, os
from flask import current_app, request, url_for
from flask_login import UserMixin, AnonymousUserMixin, current_user
from . import db, login_manager
from app.errors import ValidationError
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
from werkzeug.security import generate_password_hash, check_password_hash


class Permission(object):
    '''
    FOLLOW  关注好友
    WRITE   发表文章
    COMMENT 评论文章
    MARK    资源订阅
    GRADE   资源打分
    EVALUATE资源评价
    MANAGE  管理权限
    ADMIN   站主权限
    '''
    FOLLOW  = 0b00000001
    WRITE   = 0b00000010
    COMMENT = 0b00000100
    MARK    = 0b00001000
    GRADE   = 0b00010000
    VISIT   = 0b00100000
    MANAGE  = 0b01000000
    ADMIN   = 0b10000000


class Role(db.Model):
    '''
    权限：
    站长Admin    = FOLLOW + WRITE + COMMENT + MARK + GRADE + MANAGE + ADMIN
    管理Manager  = FOLLOW + WRITE + COMMENT + MARK + GRADE + MANAGE
    用户User     = FOLLOW + WRITE + COMMENT + MARK + GRADE
    游客Vistor   = FOLLOW + WRITE + COMMENT + MARK + GRADE + VISIT
    '''

    __tablename__ = 'roles'
    id =db.Column(db.Integer, primary_key=True)
    default = db.Column(db.Boolean, default=False, index=True)
    name = db.Column(db.String(64), unique=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role {}>'.format(self.name)

    @staticmethod
    def insert_roles():
        roles = {
            'Admin': (Permission.FOLLOW | Permission.WRITE | Permission.COMMENT |
                      Permission.MARK | Permission.GRADE |
                      Permission.MANAGE | Permission.ADMIN,
                      False),
            'Manager': (Permission.FOLLOW | Permission.WRITE | Permission.COMMENT |
                        Permission.MARK | Permission.GRADE |
                        Permission.MANAGE,
                        False),
            'User': (Permission.FOLLOW | Permission.WRITE | Permission.COMMENT |
                     Permission.MARK | Permission.GRADE ,
                     False),
            'Visitor': (Permission.FOLLOW | Permission.WRITE | Permission.COMMENT |
                        Permission.MARK | Permission.GRADE |
                        Permission.VISIT,
                        False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = role[r][1]
            db.session.add(role)
        db.session.commit()
        user = User.query.filter_by(email=current_app.config['ADMIN_EMAIL']).first()
        if user is not None:
            user.role = Role.query.filter_by(name='Admin').first()
            db.session.add(user)
        db.session.commit()


class MarkMovie(db.Model):
    __table__name = 'markmovie'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)


class MarkTV(db.Model):
    __table__name = 'marktvs'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    tv_id = db.Column(db.Integer, db.ForeignKey('tvs.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)


class MarkNovel(db.Model):
    __table__name = 'marknovels'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    novel_id = db.Column(db.Integer, db.ForeignKey('novels.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)


class MarkUploader(db.Model):
    __table__name = 'markuploaders'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('films.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)


class Follow(db.Model):
    __table__name = 'follows'
    follower_id = db.Column(db.Integer, db.Foreign('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.Foreign('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Coulmn(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    avatar_url = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    movies = db.relationship('MarkMovie',
                             foreign_keys=[MarkMovie.user_id],
                             backref=db.backref('user', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')
    tvs = db.relationship('MarkTV',
                             foreign_keys=[MarkTV.user_id],
                             backref=db.backref('user', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')
    novels = db.relationship('MarkNovel',
                             foreign_keys=[MarkNovel.user_id],
                             backref=db.backref('user', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')
    uploaders = db.relationship('MarkUploader',
                             foreign_keys=[MarkUploader.user_id],
                             backref=db.backref('user', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')
    followeds = db.relationship('Follow',
                             foreign_keys=[Follow.follower_id],
                             backref=db.backref('follower', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                             foreign_keys=[Follow.followed_id],
                             backref=db.backref('followed', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')
    realname = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['ADMIN_EMAIL']:
                self.role = Role.query.filter_by(permissions=0b11111111).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.about_me is None:
            self.about_me = '这个人很懒，什么都没留下。'
        if self.email is not None and self.avatar_url is None:
            self.avatar_url = self.gravatar()
        self.follow(self)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    @property
    def password(self):
        raise AttributeError('password不是一个可读属性。')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def make_token(self, use_for, value=None, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        data = {'user_id': self.id, 'use_for': use_for, 'value': value}
        return s.dumps(data).decode('utf-8')

    @staticmethod
    def check_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data['user_id'])
        use_for = data.get('use_for')
        value = data.get('value')
        if user.id != current_user.id:
            return False
        if use_for == 'api':
            return user.check_token_api(value)
        if use_for == 'confirm':
            return user.check_token_confirm(value)
        if use_for == 'change_password':
            return user.check_token_change_password(value)
        if use_for == 'reset_password':
            return user.check_token_reset_password(value)
        if use_for == 'reset_email':
            return user.check_token_reset_email(value)

    def check_token_api(self, value):
        return True

    def check_token_confirm(self, value):
        self.confirmed = True
        db.session.add(self)
        return True

    def check_token_change_email(self, value):
        self.email = value
        if not os.path.exists('./app' + self.avatar_url):
            self.avatar_url = self.gravatar()
        return True

    def check_token_reset_password(self, value):
        return True

    def can(self, permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def is_admin(self):
        return self.can(Permission.ADMIN)

    def ping(self):
        """视图的before_app_request钩子函数在每次请求之前调用该函数。"""
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=40, default='identicon', rating='g'):
        """__init__函数中调用，如果没有头像则赋予一个随机头像。"""
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=avatar_hash, size=size, default=default, rating=rating)

    def is_following(self, user):
        """是否关注了某个用户"""
        return self.followeds.query.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        """是否被某个用户关注"""
        return self.followers.query.filter_by(follower_id=user.id).first() is not None

    def follow(self, user):
        """添加关注用户"""
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        """移除关注用户"""
        f = self.followeds.query.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def have_marked(self, target, cls_str):
        """是否订阅了某个资源。例如cls_str='movie',getattr(self, cls_s)就是self.movies。"""
        cls_id = cls_str.lower() + '_id'
        cls_s = cls_str.lower() + 's'
        d = {cls_id: target.id}
        return getattr(self, cls_s).query.filter_by(**d).first() is not None

    def mark(self, target, cls_str):
        """添加订阅资源"""
        if not self.have_marked(target, cls_str):
            markcls = 'Mark' + cls_str.capitalize()
            d = {'user': self, cls_str: target}
            f = eval(markcls)(**d)
            db.session.add(f)

    @staticmethod
    def all_user_follow_self():
        """所有用户自我关注"""
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


role_of_movie = db.Table('role_of_movie',
                         db.Column('actor_id', db.Integer, db.ForeignKey('actors.id')),
                         db.Column('movie_id', db.Integer, db.ForeignKey('movies.id'))
                         )


role_of_tv = db.Table('role_of_movie',
                         db.Column('actor_id', db.Integer, db.ForeignKey('actors.id')),
                         db.Column('tv_id', db.Integer, db.ForeignKey('tvs.id'))
                         )


class Actor(db.Model):
    __tablename__ = 'actors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    pic_url = db.Column(db.String(128))
    movies = db.relationship('Movie', secondary=role_of_movie,
                             backref=db.backref('actors', lazy='dynamic'),
                             lazy='dynamic')
    tvs = db.relationship('TV', secondary=role_of_tv,
                             backref=db.backref('actors', lazy='dynamic'),
                             lazy='dynamic')


class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    pic_url = db.Column(db.String(128))
    users = db.relationship('MarkMovie',
                             foreign_keys=[MarkMovie.movie_id],
                             backref=db.backref('movie', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return '<Movie {}>'.format(self.name)


class TV(db.Model):
    __tablename__ = 'tvs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    pic_url = db.Column(db.String(128))
    users = db.relationship('MarkTV',
                             foreign_keys=[MarkTV.tv_id],
                             backref=db.backref('tv', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return '<TV {}>'.format(self.name)


class Novel(db.Model):
    __tablename__ = 'novels'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    pic_url = db.Column(db.String(128))
    users = db.relationship('MarkNovel',
                             foreign_keys=[MarkNovel.novel_id],
                             backref=db.backref('novel', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return '<Novel {}>'.format(self.name)


class Uploader(db.Model):
    __tablename__ = 'uploaders'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    pic_url = db.Column(db.String(128))
    users = db.relationship('MarkUploader',
                             foreign_keys=[MarkUploader.uploader_id],
                             backref=db.backref('uploader', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return '<Uploader {}>'.format(self.name)




