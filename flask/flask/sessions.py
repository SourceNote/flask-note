# -*- coding: utf-8 -*-
"""
    flask.sessions：使用itsdangerous实现基于cookie的session
"""

import hashlib
import warnings
from collections import MutableMapping
from datetime import datetime

from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.datastructures import CallbackDict

from flask.helpers import is_ip, total_seconds
from flask.json.tag import TaggedJSONSerializer


class SessionMixin(MutableMapping):
    """给一个基础字典设置session属性进行扩展"""

    @property
    def permanent(self):
        """反射字典中的`_permanent`"""
        return self.get('_permanent', False)

    @permanent.setter
    def permanent(self, value):
        self['_permanent'] = bool(value)  # 注意这里进行了强制类型转换

    #: Some implementations can detect whether a session is newly
    #: created, but that is not guaranteed. Use with caution. The mixin
    # default is hard-coded ``False``.
    # 缺省硬编码为False，session是否是新创建的
    new = False

    #: Some implementations can detect changes to the session and set
    #: this when that happens. The mixin default is hard coded to
    #: ``True``.
    # 缺省硬编码为True，session是否被更改
    modified = True

    #: Some implementations can detect when session data is read or
    #: written and set this when that happens. The mixin default is hard
    #: coded to ``True``.
    # 缺省硬编码为True，session是否被访问
    accessed = True


class SecureCookieSession(CallbackDict, SessionMixin):  # 这里有个疑惑点：继承顺序
    """基于签名cookie实现的session基类."""

    # 当数据被改变，被设置为True；如果session字典包含可修改数据（比如说嵌套字典）
    # 一定要在修改数据的和时候手动设置为True
    # 只有此字段为True时session cookie才会被写进响应
    modified = False

    # 数据被访问时（读或写），被设置为True
    # .SecureCookieSessionInterface使用来添加Vary: Cookie头
    # 以允许缓存代理针对不同的用户缓存不同的页面
    accessed = False

    def __init__(self, initial=None):
        def on_update(self):
            # 发生更新就更新下面两个字段
            self.modified = True
            self.accessed = True

        super(SecureCookieSession, self).__init__(initial, on_update)

    def __getitem__(self, key):
        self.accessed = True
        return super(SecureCookieSession, self).__getitem__(key)

    def get(self, key, default=None):
        self.accessed = True  # 设置字段更新
        return super(SecureCookieSession, self).get(key, default)

    def setdefault(self, key, default=None):
        self.accessed = True  # 设置字段更新
        return super(SecureCookieSession, self).setdefault(key, default)


class NullSession(SecureCookieSession):
    """空Session类，可访问，不可被设置，为了提供更有好的错误信息"""

    def _fail(self, *args, **kwargs):
        raise RuntimeError('The session is unavailable because no secret '
                           'key was set.  Set the secret_key on the '
                           'application to something unique and secret.')

    # 所有修改相关的操作全部设置为抛出相关异常的方法
    __setitem__ = __delitem__ = clear = pop = popitem = \
        update = setdefault = _fail
    del _fail


class SessionInterface(object):
    """The basic interface you have to implement in order to replace the
    default session interface which uses werkzeug's securecookie
    implementation.  The only methods you have to implement are
    :meth:`open_session` and :meth:`save_session`, the others have
    useful defaults which you don't need to change.

    The session object returned by the :meth:`open_session` method has to
    provide a dictionary like interface plus the properties and methods
    from the :class:`SessionMixin`.  We recommend just subclassing a dict
    and adding that mixin::

        class Session(dict, SessionMixin):
            pass

    If :meth:`open_session` returns ``None`` Flask will call into
    :meth:`make_null_session` to create a session that acts as replacement
    if the session support cannot work because some requirement is not
    fulfilled.  The default :class:`NullSession` class that is created
    will complain that the secret key was not set.

    To replace the session interface on an application all you have to do
    is to assign :attr:`flask.Flask.session_interface`::

        app = Flask(__name__)
        app.session_interface = MySessionInterface()

    .. versionadded:: 0.8
    """

    #: :meth:`make_null_session` will look here for the class that should
    #: be created when a null session is requested.  Likewise the
    #: :meth:`is_null_session` method will perform a typecheck against
    #: this type.
    null_session_class = NullSession

    #: A flag that indicates if the session interface is pickle based.
    #: This can be used by Flask extensions to make a decision in regards
    #: to how to deal with the session object.
    #:
    #: .. versionadded:: 0.10
    pickle_based = False

    def make_null_session(self, app):
        """创建空session"""
        return self.null_session_class()

    def is_null_session(self, obj):
        """检查是否是空session"""
        return isinstance(obj, self.null_session_class)

    def get_cookie_domain(self, app):
        """
        获取cookie应该被设置的域名
        获取优先级：app配置SESSION_COOKIE_DOMAIN->SERVER_NAME
        一旦侦测到SESSION_COOKIE_DOMAIN就会被更新，以免重复运行
        :param app:
        :return:
        """

        rv = app.config['SESSION_COOKIE_DOMAIN']

        # set explicitly, or cached from SERVER_NAME detection
        # if False, return None
        if rv is not None:
            # 这样写要对照下面的SERVER_NAME
            # 防止重复运行
            return rv if rv else None

        rv = app.config['SERVER_NAME']

        # server name not set, cache False to return none next time
        if not rv:
            app.config['SESSION_COOKIE_DOMAIN'] = False
            return None

        # 移除端口号：浏览器通常不支持
        # 一处开头的.,因为稍后会加上
        rv = rv.rsplit(':', 1)[0].lstrip('.')

        if '.' not in rv:
            # Chrome浏览器不允许没有.
            # this should only come up with localhost
            # hack around this by not setting the name, and show a warning
            warnings.warn(
                '"{rv}" is not a valid cookie domain, it must contain a ".".'
                ' Add an entry to your hosts file, for example'
                ' "{rv}.localdomain", and use that instead.'.format(rv=rv)
            )
            app.config['SESSION_COOKIE_DOMAIN'] = False
            return None

        ip = is_ip(rv)

        if ip:
            warnings.warn(
                'The session cookie domain is an IP address. This may not work'
                ' as intended in some browsers. Add an entry to your hosts'
                ' file, for example "localhost.localdomain", and use that'
                ' instead.'
            )

        # if this is not an ip and app is mounted at the root, allow subdomain
        # matching by adding a '.' prefix
        if self.get_cookie_path(app) == '/' and not ip:
            rv = '.' + rv

        app.config['SESSION_COOKIE_DOMAIN'] = rv
        return rv

    def get_cookie_path(self, app):
        """获取cookie路径
        优先级：配置中的SESSION_COOKIE_PATH->APPLICATION_ROOT->/
        """
        return app.config['SESSION_COOKIE_PATH'] \
               or app.config['APPLICATION_ROOT']

    def get_cookie_httponly(self, app):
        """Returns True if the session cookie should be httponly.  This
        currently just returns the value of the ``SESSION_COOKIE_HTTPONLY``
        config var.
        """
        return app.config['SESSION_COOKIE_HTTPONLY']

    def get_cookie_secure(self, app):
        """Returns True if the cookie should be secure.  This currently
        just returns the value of the ``SESSION_COOKIE_SECURE`` setting.
        """
        return app.config['SESSION_COOKIE_SECURE']

    def get_cookie_samesite(self, app):
        """Return ``'Strict'`` or ``'Lax'`` if the cookie should use the
        ``SameSite`` attribute. This currently just returns the value of
        the :data:`SESSION_COOKIE_SAMESITE` setting.
        """
        return app.config['SESSION_COOKIE_SAMESITE']

    def get_expiration_time(self, app, session):
        """获取session的过期时间"""
        """A helper method that returns an expiration date for the session
        or ``None`` if the session is linked to the browser session.  The
        default implementation returns now + the permanent session
        lifetime configured on the application.
        """
        if session.permanent:  # 如果是永久的
            return datetime.utcnow() + app.permanent_session_lifetime

    def should_set_cookie(self, app, session):
        """Used by session backends to determine if a ``Set-Cookie`` header
        should be set for this session cookie for this response. If the session
        has been modified, the cookie is set. If the session is permanent and
        the ``SESSION_REFRESH_EACH_REQUEST`` config is true, the cookie is
        always set.

        This check is usually skipped if the session was deleted.

        .. versionadded:: 0.11
        """

        return session.modified or (
                session.permanent and app.config['SESSION_REFRESH_EACH_REQUEST']
        )

    def open_session(self, app, request):
        """This method has to be implemented and must either return ``None``
        in case the loading failed because of a configuration error or an
        instance of a session object which implements a dictionary like
        interface + the methods and attributes on :class:`SessionMixin`.
        """
        raise NotImplementedError()

    def save_session(self, app, session, response):
        """This is called for actual sessions returned by :meth:`open_session`
        at the end of the request.  This is still called during a request
        context so if you absolutely need access to the request you can do
        that.
        """
        raise NotImplementedError()


session_json_serializer = TaggedJSONSerializer()  # Session JSON序列化器


class SecureCookieSessionInterface(SessionInterface):
    """The default session interface that stores sessions in signed cookies
    through the :mod:`itsdangerous` module.
    """
    #: the salt that should be applied on top of the secret key for the
    #: signing of cookie based sessions.
    salt = 'cookie-session'
    #: the hash function to use for the signature.  The default is sha1
    digest_method = staticmethod(hashlib.sha1)
    #: the name of the itsdangerous supported key derivation.  The default
    #: is hmac.
    key_derivation = 'hmac'
    #: A python serializer for the payload.  The default is a compact
    #: JSON derived serializer with support for some extra Python types
    #: such as datetime objects or tuples.
    serializer = session_json_serializer
    session_class = SecureCookieSession

    def get_signing_serializer(self, app):
        if not app.secret_key:
            return None
        signer_kwargs = dict(
            key_derivation=self.key_derivation,
            digest_method=self.digest_method
        )
        return URLSafeTimedSerializer(app.secret_key, salt=self.salt,
                                      serializer=self.serializer,
                                      signer_kwargs=signer_kwargs)

    def open_session(self, app, request):
        """读取request中的cookie"""
        s = self.get_signing_serializer(app)
        if s is None:
            return None
        val = request.cookies.get(app.session_cookie_name)
        if not val:
            return self.session_class()
        max_age = total_seconds(app.permanent_session_lifetime)
        try:
            data = s.loads(val, max_age=max_age)
            return self.session_class(data)
        except BadSignature:
            return self.session_class()

    def save_session(self, app, session, response):
        """将cookie写到response"""
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)

        # If the session is modified to be empty, remove the cookie.
        # If the session is empty, return without setting the cookie.
        if not session:
            if session.modified:
                response.delete_cookie(
                    app.session_cookie_name,
                    domain=domain,
                    path=path
                )

            return

        # Add a "Vary: Cookie" header if the session was accessed at all.
        if session.accessed:
            response.vary.add('Cookie')

        if not self.should_set_cookie(app, session):
            return

        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)
        samesite = self.get_cookie_samesite(app)
        expires = self.get_expiration_time(app, session)
        val = self.get_signing_serializer(app).dumps(dict(session))
        response.set_cookie(
            app.session_cookie_name,
            val,
            expires=expires,
            httponly=httponly,
            domain=domain,
            path=path,
            secure=secure,
            samesite=samesite
        )
