# -*- coding: utf-8 -*-
"""
    __init__.py：为了使用的方便进行的导入和重命名
"""

__version__ = '1.0'

# 从Werkzeug and Jinja2 中的倒入的本模块未使用的工具
# 用来暴露为公开接口
from werkzeug.exceptions import abort
from werkzeug.utils import redirect
from jinja2 import Markup, escape

from .app import Flask, Request, Response
from .config import Config
from .helpers import url_for, flash, send_file, send_from_directory, \
    get_flashed_messages, get_template_attribute, make_response, safe_join, \
    stream_with_context
from .globals import current_app, g, request, session, _request_ctx_stack, \
    _app_ctx_stack
from .ctx import has_request_context, has_app_context, \
    after_this_request, copy_current_request_context
from .blueprints import Blueprint
from .templating import render_template, render_template_string

# 信号
from .signals import signals_available, template_rendered, request_started, \
    request_finished, got_request_exception, request_tearing_down, \
    appcontext_tearing_down, appcontext_pushed, \
    appcontext_popped, message_flashed, before_render_template

# 没有暴露真的json接口，而是导出它的一个封装
from . import json

# 只是为了简便，alias.
jsonify = json.jsonify

# 向后兼容
from .sessions import SecureCookieSession as Session

json_available = True
